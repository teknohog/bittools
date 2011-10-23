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

def prettyprint(array, delimiter=""):
    width = max(map(lambda x: printlength(x[0]), array)) + 1
    for i in array:
        print(i[0] + delimiter + " "*(width - printlength(i[0])) + str(i[1]))

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
    if options.namecoin:
        return 50
    else:
        # Initially 50 bitcoins per block, halved every 210000 blocks
        c = 210000.0
        p = ceil(blocks / c)
        return 50 * 0.5**(p - 1)

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

def listreceived():
    rec = s.listreceivedbyaccount()

    if len(rec) > 0:
        output = []
        for item in rec:
            output.append([str(item["account"]), item["amount"]])
    
        prettyprint(output)

def listtransactions():
    # The ctime string has a fixed length, so we can combine it into a
    # string with the account name, and keep using the 2-column
    # prettyprint function.

    trans = s.listtransactions()

    if len(trans) > 0:
        output = []
        for item in trans:
            unconfirmed = (item["confirmations"] < int(options.min_confirm))
            output.append([ctime(item["time"]) + " " + item["account"], str(item["amount"]) + unconfirmed * " *"])

        prettyprint(output)

def send(address, amount):
    # Double check the amount and address -- the command line may be
    # split over two lines, making the amount less obvious
    print("About to send " + currency + " " + str(amount) + " to " + address)

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

parser.add_option("-a", "--allinfo", dest="allinfo", action="store_true", default=False, help="Print complete getinfo")

parser.add_option("-c", "--confirmations", dest="min_confirm", default=1, help="Warn when there are fewer confirmations for a transaction, default 1")

parser.add_option("-d", "--difficulty", dest="diff", help="Set difficulty for mining calculator")

parser.add_option("-l", "--listreceived", dest="listreceived", action="store_true", default=False, help="List totals received by account/label")

parser.add_option("-n", "--namecoin", dest="namecoin", action="store_true", default=False, help="Connect to namecoind instead, and display payouts accordingly")

parser.add_option("-r", "--hashrate", dest="hashrate", help="Hashes/sec from external miners, e.g. 250e6")

parser.add_option("-s", "--sendto", dest="sendto", help="Send coins to this address, followed by the amount")

parser.add_option("-t", "--transactions", dest="transactions", action="store_true", default=False, help="List recent transactions")

parser.add_option("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local bitcoind")

(options, args) = parser.parse_args()

if options.namecoin:
    currency = "NMC"
else:
    currency = "BTC"

if len(options.url) > 0:
    url = options.url
else:
    if options.namecoin:
        configfile = "~/.namecoin/bitcoin.conf"
    else:
        configfile = "~/.bitcoin/bitcoin.conf"

    settings = parse_config(configfile)

    if not 'rpcport' in settings.keys():
        # Default for both bitcoind and namecoind
        settings['rpcport'] = "8332"

    url = "http://" + settings['rpcuser'] + ":" + settings['rpcpassword'] + "@127.0.0.1:" + settings['rpcport'] + "/"

s = ServiceProxy(url)

if options.listreceived:
    listreceived()
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
    keys = ["balance", "difficulty", "testnet"]

output = []
for key in keys:
    output.append([key, info[key]])

prettyprint(output)

if options.diff:
    diff = float(options.diff)
else:
    diff = info["difficulty"]

if options.hashrate:
    hashrate = float(options.hashrate)
else:
    hashrate = info["hashespersec"]

blocks = info["blocks"]

output = []

if hashrate > 0:
    time = diff * 2**32 / hashrate
    tp = timeprint(time)

    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])

    coinrate = block_coins(blocks) / tp[0]

    output.append(["Average payout", str(coinrate) + " " + currency + "/" + tp[1]])

# Target rate is 6 blocks per hour, diff adjusted every 14 days
fortnight = 6 * 24 * 14

time = (fortnight - blocks % fortnight) / 6. * 3600

tp = timeprint(time)
output.append(["\nNext difficulty expected in", str(tp[0]) + " " + tp[1]])

errors = info["errors"]
if len(errors) > 0:
    output.append(["\nError", errors])

prettyprint(output)
