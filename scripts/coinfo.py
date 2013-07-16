#!/usr/bin/env python

# by teknohog, iki.fi

# Provides simple access to some of the bitcoind functions, with some
# extras like difficulty calculations for other miners/difficulties.

# Payment has extra warnings and confirmations to guard against dupes,
# which may easily happen on the command line. At the moment, there
# are no checks for valid bitcoin addresses etc. but bitcoind should
# take care of these.

# By default, the JSON-RPC credentials are read from
# ~/.bitcoin/bitcoin.conf and this connects to localhost. Or provide
# another complete URL.

# module installed via svn from http://json-rpc.org/wiki/python-json-rpc
from jsonrpc import ServiceProxy
import sys
from optparse import OptionParser
import os.path
import re
from math import ceil
from time import ctime

def printlength(s):
    # get rid of newlines for the printable length calculation
    return len(s.replace("\n", ""))

def prettyprint(array, delimiter=" "):
    # I guess this verges on something that should use curses instead
    columns = len(array[0])

    width = []
    for column in range(columns):
        width.append(max(map(lambda x: printlength(x[column]), array)))

    for i in array:
        print(delimiter.join(map(lambda col: i[col] + " "*(width[col] - printlength(i[col])), range(columns - 1))) + delimiter + i[columns-1])

def timeprint(time):
    # This is used more generally, so provide the number as a number,
    # and the unit separately

    if time >= 86400:
        return [time / 86400, "d"]
    elif time >= 3600:
        return [time / 3600, "h"]
    elif time >= 60:
        return [time / 60, "min"]
    else:
        return [time, "s"]

def block_coins(blocks):
    if coin == "namecoin":
        return 50
    else:
        c = blockhalve[coin] - 2

        p = ceil(blocks / c)
        return initcoins[coin] * 0.5**(p - 1)

def parse_config(conffile):
    # config file parsing shamelessly adapted from jgarzik's pyminer, as
    # Python's configparser insists on having sections

    # teknohog changed this from search to match, as the simpler
    # version is enough here.

    settings = {}
    config = ReadLines(os.path.expanduser(conffile))
    for line in config:
        # skip comment lines
        m = re.match('\s*#', line)
        if m:
            continue
        
        # parse key=value lines                                         
        m = re.match('(\w+)\s*=\s*(\S.*)$', line)
        if m is None:
            continue
        settings[m.group(1)] = m.group(2)

    return settings

def ReadLines(file):
    File = open(file, "r")
    contents = File.readlines()
    File.close()
    return contents

def exportkeys():
    accounts = s.listaccounts()
    
    l = []

    for acc in accounts:
        addresses = s.getaddressesbyaccount(acc)
        for addr in addresses:
            privkey = s.dumpprivkey(addr)
            l.append([privkey, acc])
            
    prettyprint(l)

def importkeys(file):
    lines = ReadLines(file)

    for line in lines:
        # Account names may contain spaces, so split only once to get the key
        l = line.split(" ", 1)
        privkey = l[0]

        lineno = lines.index(line) + 1

        if len(privkey) not in [51, 52]:
            print("Invalid private key %s on line %i ignored" % (privkey, lineno))
            continue

        if len(l) > 1:
            # There is always a trailing newline to remove; other
            # leading/trailing spaces will be removed too, which
            # should be ok
            acc = l[1].strip()
            s.importprivkey(privkey, acc)
        else:
            # No account specified, which is also allowed
            s.importprivkey(privkey)

        # bitcoind takes time to import a key, so give some progress indication
        print("Key # %i imported" % lineno)

def listaccounts():
    acc = s.listaccounts()

    if len(acc) > 0:
        output = []
        for item in acc:
            output.append([item, str(acc[item])])
    
        prettyprint(output)

def listreceived():
    rec = s.listreceivedbyaccount()

    if len(rec) > 0:
        output = []
        for item in rec:
            output.append([item["account"], str(item["amount"])])
    
        prettyprint(output)

def listtransactions():
    trans = s.listtransactions()

    if len(trans) > 0:
        output = []
        for item in trans:
            unconfirmed = item["confirmations"] < int(options.min_confirm) or item["category"] == "immature"
            output.append([ctime(item["time"]), transcat[item["category"]], item["account"], str(item["amount"]), unconfirmed * "*"])

        prettyprint(output)

def send(address, amount):
    # Double check the amount and address -- the command line may be
    # split over two lines, making the amount less obvious
    print("About to send " + currency[coin] + " " + str(amount) + " to " + address)

    # Warn of potential dupes
    trans = s.listtransactions()
    if len(trans) > 0:
        for item in trans:
            if "address" in item.keys() and address == item["address"]:
                print("Warning! " + str(abs(item["amount"])) + " already sent to this address on " + ctime(item["time"]))
                
    # Ask for confirmation by typing/copying a random string
    from random import sample, randrange
    import string
    chars = string.ascii_letters + string.digits
    conf = string.join(sample(chars, randrange(6, 15)), "")
    c_input = raw_input("Please type " + conf + " to confirm the transaction: ")
    if c_input == conf:
        try:
            result = s.sendtoaddress(address, amount)
            print("Sent " + str(amount) + " to " + address + " with txid")
            print(result)
        except:
            print("Send failed")
    else:
        print("Confirmation failed, not sending.")

parser = OptionParser()

parser.add_option("-A", "--listaccounts", dest="listaccounts", action="store_true", default=False, help="List accounts with balances")

parser.add_option("-a", "--allinfo", dest="allinfo", action="store_true", default=False, help="Print complete getinfo")

parser.add_option("-b", "--byaccount", dest="byaccount", help="List addresses by the given account")

parser.add_option("-c", "--chncoin", action="store_const", const="chncoin", dest="coin", default="bitcoin", help="Connect to chncoind")

parser.add_option("-C", "--confirmations", dest="min_confirm", default=1, help="Warn when there are fewer confirmations for a transaction, default 1")

parser.add_option("-d", "--difficulty", dest="diff", help="Set difficulty for mining calculator")

parser.add_option("-e", "--exportkeys", dest="export", action="store_true", default=False, help="Export all private keys, along with account names")

parser.add_option("-i", "--importkeys", dest="importfile", help="Import private keys from file (see exportkeys output for formatting)")

parser.add_option("-l", "--litecoin", action="store_const", const="litecoin", dest="coin", default="bitcoin", help="Connect to litecoind")

parser.add_option("-N", "--newaddress", dest="newaddress", action="store_true", default=False, help="Get new address, optionally for the given account")

parser.add_option("-n", "--namecoin", action="store_const", const="namecoin", dest="coin", default="bitcoin", help="Connect to namecoind")

parser.add_option("-P", "--primecoin", action="store_const", const="primecoin", dest="coin", default="bitcoin", help="Connect to primecoind")

parser.add_option("-p", "--ppcoin", action="store_const", const="ppcoin", dest="coin", default="bitcoin", help="Connect to ppcoind")

parser.add_option("-R", "--listreceived", dest="listreceived", action="store_true", default=False, help="List totals received by account/label")

parser.add_option("-r", "--hashrate", dest="hashrate", help="Hashes/sec from external miners, e.g. 250e6")

parser.add_option("-s", "--sendto", dest="sendto", help="Send coins to this address, followed by the amount")

parser.add_option("-t", "--transactions", dest="transactions", action="store_true", default=False, help="List recent transactions")

parser.add_option("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local bitcoind")

(options, args) = parser.parse_args()

coin = options.coin

# Transaction categories; an immature block is a generated one, and
# the immaturity is shown with a * like unconfirmed ones.
transcat = {
    "generate": "G",
    "immature": "G",
    "orphan": "O",
    "receive": "R",
    "send": "S",
}

# coin-dependent constants
currency = {
    "bitcoin": "BTC",
    "chncoin": "CNC",
    "litecoin": "LTC",
    "namecoin": "NMC",
    "ppcoin": "PPC",
    "primecoin": "XPM",
}

blockhalve = {
    "bitcoin": 210000.0,
    "chncoin": 2628000.0,
    "litecoin": 840000.0,
    "namecoin": 210000.0,
}

blocksperhour = {
    "bitcoin": 6.,
    "chncoin": 60.,
    "litecoin": 24.,
    "namecoin": 6.,
    "primecoin": 60.,
}

adjustblocks = {
    "bitcoin": 2016,
    "chncoin": 5040,
    "litecoin": 2016,
    "namecoin": 2016,
}

initcoins = {
    "bitcoin": 50,
    "chncoin": 88,
    "namecoin": 50,
    "litecoin": 50,
}

rpcport = {
    "bitcoin": "8332",
    "chncoin": "8108",
    "litecoin": "9332",
    "namecoin": "8332",
    "ppcoin": "9902",
    "primecoin": "9912",
}

if len(options.url) > 0:
    url = options.url
else:
    configfile = "~/." + coin + "/" + coin + ".conf"

    settings = parse_config(configfile)

    # Use default port numbers
    if not 'rpcport' in settings.keys():
        settings['rpcport'] = rpcport[coin]

    url = "http://" + settings['rpcuser'] + ":" + settings['rpcpassword'] + "@127.0.0.1:" + settings['rpcport'] + "/"

s = ServiceProxy(url)

if options.byaccount:
    for addr in s.getaddressesbyaccount(options.byaccount):
        print(addr)
    sys.exit()

if options.export:
    exportkeys()
    sys.exit()

if options.importfile:
    importkeys(options.importfile)
    sys.exit()

if options.listaccounts:
    listaccounts()
    sys.exit()

if options.listreceived:
    listreceived()
    sys.exit()

if options.newaddress:
    print(s.getnewaddress(args[0]))
    sys.exit()

if options.sendto:
    send(options.sendto, float(args[0]))
    sys.exit()

if options.transactions:
    listtransactions()
    sys.exit()

info = s.getinfo()

if options.allinfo:
    keys = info.keys()
else:
    # Primecoin does not provide difficulty in getinfo, only separately
    keys = ["balance", "testnet"]

if options.diff:
    diff = float(options.diff)
else:
    diff = s.getdifficulty()

output = []
for key in keys:
    output.append([key, str(info[key])])

# Primecoin above
output.append(["difficulty", str(diff)])

if options.hashrate:
    hashrate = float(options.hashrate)
    # No point in printing this, if supplied manually
else:
    if coin == "primecoin":
        hashrate = s.getprimespersec()
        if options.allinfo:
            output.append(["primespersec", str(hashrate)])
    else:
        hashrate = s.gethashespersec()
        if options.allinfo:
            output.append(["hashespersec", str(hashrate)])

prettyprint(output)

blocks = info["blocks"]

output = []

if hashrate > 0:
    if coin == "primecoin":
        # block reward = 999 / diff**2
        # but the rest of the calculation still TODO...
        pass
    else:
        # ppcoin
        if type(diff) == dict:
            diff = diff['proof-of-work']

        time = diff * 2**32 / hashrate
        tp = timeprint(time)
    
        output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])

        if coin == "ppcoin":
            # https://bitcointalk.org/index.php?topic=101820.msg1118737#msg1118737
            # "The block reward for a work block is sqrt(sqrt(9999^4 /
            # difficulty)), rounded down to the next cent boundary."
            coinrate = int(999900. / diff**0.25) / (100 * tp[0])
        else:
            coinrate = block_coins(blocks) / tp[0]
        
        output.append(["Average payout", str(coinrate) + " " + currency[coin] + "/" + tp[1]])

# These coins have a dynamic adjustment without fixed intervals.
if coin not in ["ppcoin", "primecoin"]:
    time = (adjustblocks[coin] - blocks % adjustblocks[coin]) / blocksperhour[coin] * 3600
    tp = timeprint(time)
    output.append(["\nNext difficulty expected in", str(tp[0]) + " " + tp[1]])

errors = info["errors"]
if len(errors) > 0:
    output.append(["\nError", errors])

if len(output) > 0:
    prettyprint(output)
