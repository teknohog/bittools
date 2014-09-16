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
        return [time / 86400, "days"]
    elif time >= 3600:
        return [time / 3600, "h"]
    elif time >= 60:
        return [time / 60, "min"]
    else:
        return [time, "s"]

def staired_reward(blocks, reward_stairs):
    (limits, rewards) = reward_stairs

    for i in range(len(limits)):
        if blocks < limits[i]:
            return rewards[i-1]

    return rewards[-1]

def groestl_reward(blocks):
    if blocks >= 150000:
        return exp_decay(25, blocks-150000, 10080, 0.99)

    if blocks >= 120000:
        return exp_decay(250, blocks-120000, 1440, 0.9)

    # Default to old scheme
    return exp_decay(512, blocks, 10080, 0.94)

def exp_decay(init, blocks, period, base=0.5):
    p = ceil(float(blocks) / float(period - 2))
    return init * base**(p - 1)

def blockreward(coin, diff, blocks):
    if coin == "ppcoin":
        # https://bitcointalk.org/index.php?topic=101820.msg1118737#msg1118737
        # "The block reward for a work block is sqrt(sqrt(9999^4 /
        # difficulty)), rounded down to the next cent boundary."
        return int(999900. / diff**0.25) / 100.
    elif coin == "primecoin":
        # block reward = 999 / diff**2, likewise floored to cent
        return int(99900. / diff**2) / 100.
    elif coin in ["blakecoin", "photon"]:
        return initcoins[coin] + round((blocks * diff * 256)**0.5) * 1e-8
    elif coin == "darkcoin":
        return max(2222222. / (((diff + 2600.)/9.)**2), 5.0)
    elif coin == "GroestlCoin":
        return groestl_reward(blocks)
    elif coin in reward_stairs.keys():
        return staired_reward(blocks, reward_stairs[coin])
    elif coin in blockhalve.keys() and blockhalve[coin] == 0:
        return initcoins[coin]
    elif coin == "virtacoin":
        # 8000 coins per block, reduces by 0.5% each week starting 2/28/14
        return exp_decay(8000, blocks, 10080, 0.995)
    elif coin == "cryptonite":
        coinbase = ep_dec(s.listbalances(1, ["CGTta3M4t3yXu8uRgkKvaWd2d8DQvDPnpL"])[0]["balance"])
        final_total = (2**64 - 1) * 1e-10
        return 243.1 * coinbase / final_total
    else:
        return exp_decay(initcoins[coin], blocks, blockhalve[coin])

# Extended precision float encoding for Cryptonite
def ep_enc(x):
    return '%.10fep' % x

def ep_dec(s):
    return float(s.rstrip('ep'))

def own_share(coin, blocks, info):
    total = 0
    final_total = 0
    printout = []

    # This should really be made more generic, like blockhalve, but
    # this will do until more coins come up with different exp bases.
    if coin == "virtacoin":
        base = 0.995
    else:
        base = 0.5

    if coin in reward_stairs.keys():
        # Current reward algo tells us which cycle is on
        reward = staired_reward(blocks, reward_stairs[coin])
        cycle = reward_stairs[coin][1].index(reward)

        # Total over finished cycles
        total = sum([(reward_stairs[coin][0][j+1] - reward_stairs[coin][0][j]) * reward_stairs[coin][1][j] for j in range(cycle)])

        # + total over current cycle
        total += (blocks - reward_stairs[coin][0][cycle]) * reward

    elif coin in blockhalve.keys() and blockhalve[coin] > 0:
        reward = exp_decay(initcoins[coin], blocks, blockhalve[coin])
        fullcycles = int(blocks / blockhalve[coin])
        
        # Total over finished halving cycles
        total = (1 - base**fullcycles) / (1 - base) * blockhalve[coin] * initcoins[coin]

        # + total over current cycle
        total += (blocks - fullcycles * blockhalve[coin]) * reward

        final_total = blockhalve[coin] / (1 - base) * initcoins[coin]

    elif coin in ["blakecoin", "photon", "namecoin"]:
        total = blocks * initcoins[coin]

    elif "moneysupply" in info:
        total = info["moneysupply"]

    elif coin == "cryptonite":
        # Coinbase address
        coinbase = ep_dec(s.listbalances(1, ["CGTta3M4t3yXu8uRgkKvaWd2d8DQvDPnpL"])[0]["balance"])
        final_total = (2**64 - 1) * 1e-10
        total = final_total - coinbase
        info["balance"] = ep_dec(info["balance"])

    if total > 0 and info["balance"] > 0:
        share = info["balance"] / total
        printout.append([str(share * 100), str(int(round(1/share))) + " of all current " + currency[coin]])

    if final_total > 0 and info["balance"] > 0:
        share = info["balance"] / final_total
        printout.append([str(share * 100), str(int(round(1/share))) + " of all " + currency[coin] + " ever"])

    if len(printout) > 0:
        print("\nYour balance represents about")
        prettyprint(printout, " % or 1/")

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

def coin_price(coin):
    # Assume EUR as the base price for now
    cn_url = "https://www.cryptonator.com/api/ticker/" + currency[coin] + "-EUR"

    # http://stackoverflow.com/questions/12965203/how-to-get-json-from-webpage-into-python-script
    import urllib, json

    response = urllib.urlopen(cn_url);
    data = json.loads(response.read())

    if "ticker" in data.keys():
        return float(data["ticker"]["price"])
    else:
        return 0

def ReadLines(file):
    File = open(file, "r")
    contents = File.readlines()
    File.close()
    return contents

def exportkeys():
    # Generate addresses are not available via accounts, even though
    # they are listed under the "" account. So this way should get us
    # all possible addresses...

    l = []

    # Method not available in ppcoin
    try:
        g = s.listaddressgroupings()
        for group in g:
            for addrline in group:
                address = addrline[0]
                privkey = s.dumpprivkey(address)

                if len(addrline) == 3:
                    account = addrline[2]
                else:
                    account = ""

                l.append([privkey, account])
    except:
        print("Warning: missing listaddressgroupings method, list of keys may be incomplete\n")

    # ..but the above seems to leave out addresses with zero balance,
    # so use the old way too, and check for dupes.

    accounts = s.listaccounts()

    for acc in accounts:
        addresses = s.getaddressesbyaccount(acc)
        for addr in addresses:
            privkey = s.dumpprivkey(addr)
            item = [privkey, acc]
            
            if item not in l:
                l.append(item)

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
            if "address" in item.keys():
                address = item["address"]
            else:
                address = ""
            output.append([ctime(item["time"]), item["category"][0].upper(), item["account"], str(item["amount"]), unconfirmed * "*", options.verbose * address, options.verbose * str(item["confirmations"])])

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
            if coin == "cryptonite":
                result = s.sendtoaddress(address, ep_enc(amount))
            else:
                result = s.sendtoaddress(address, amount)

            print("Sent " + str(amount) + " to " + address + " with txid")
            print(result)
        except:
            print("Send failed")
    else:
        print("Confirmation failed, not sending.")

parser = OptionParser()

parser.add_option("-A", "--listaccounts", dest="listaccounts", action="store_true", default=False, help="List accounts with balances")

parser.add_option("-a", "--AuroraCoin", action="store_const", const="AuroraCoin", dest="coin", default="bitcoin", help="Connect to AuroraCoind")

parser.add_option("-B", "--blakecoin", action="store_const", const="blakecoin", dest="coin", default="bitcoin", help="Connect to blakecoind")

parser.add_option("-b", "--byaccount", dest="byaccount", help="List addresses by the given account")

parser.add_option("--bitcoin", action="store_const", const="bitcoin", dest="coin", default="bitcoin", help="Connect to bitcoind")

parser.add_option("-c", "--chncoin", action="store_const", const="chncoin", dest="coin", default="bitcoin", help="Connect to chncoind")

parser.add_option("-C", "--confirmations", dest="min_confirm", default=1, help="Warn when there are fewer confirmations for a transaction, default 1")

parser.add_option("-d", "--difficulty", dest="diff", help="Set difficulty for mining calculator")

parser.add_option("-D", "--dogecoin", action="store_const", const="dogecoin", dest="coin", default="bitcoin", help="Connect to dogecoind")

parser.add_option("--ecoin", action="store_const", const="ecoin", dest="coin", default="bitcoin", help="Connect to ecoind")

parser.add_option("-E", "--electron", action="store_const", const="electron", dest="coin", default="bitcoin", help="Connect to electrond")

parser.add_option("-e", "--exportkeys", dest="export", action="store_true", default=False, help="Export all private keys, along with account names")

parser.add_option("-G", "--GroestlCoin", action="store_const", const="GroestlCoin", dest="coin", default="bitcoin", help="Connect to GroestlCoind")

parser.add_option("-g", "--ShibeCoin", action="store_const", const="ShibeCoin", dest="coin", default="bitcoin", help="Connect to ShibeCoind")

parser.add_option("-H", "--photon", action="store_const", const="photon", dest="coin", default="bitcoin", help="Connect to photond")

parser.add_option("-I", "--riecoin", action="store_const", const="riecoin", dest="coin", default="bitcoin", help="Connect to riecoind")

parser.add_option("-i", "--importkeys", dest="importfile", help="Import private keys from file (see exportkeys output for formatting)")

parser.add_option("-j", "--primio", action="store_const", const="primio", dest="coin", default="bitcoin", help="Connect to primiod")

parser.add_option("-K", "--darkcoin", action="store_const", const="darkcoin", dest="coin", default="bitcoin", help="Connect to darkcoind")

parser.add_option("-k", "--blakebitcoin", action="store_const", const="blakebitcoin", dest="coin", default="bitcoin", help="Connect to blakebitcoind")

parser.add_option("-L", "--SlothCoin", action="store_const", const="SlothCoin", dest="coin", default="bitcoin", help="Connect to SlothCoind")

parser.add_option("-l", "--litecoin", action="store_const", const="litecoin", dest="coin", default="bitcoin", help="Connect to litecoind")

parser.add_option("-N", "--newaddress", dest="newaddress", action="store_true", default=False, help="Get new address, optionally for the given account")

parser.add_option("-m", "--maxcoin", action="store_const", const="maxcoin", dest="coin", default="bitcoin", help="Connect to maxcoind")

parser.add_option("-n", "--namecoin", action="store_const", const="namecoin", dest="coin", default="bitcoin", help="Connect to namecoind")

parser.add_option("-P", "--primecoin", action="store_const", const="primecoin", dest="coin", default="bitcoin", help="Connect to primecoind")

parser.add_option("-p", "--ppcoin", action="store_const", const="ppcoin", dest="coin", default="bitcoin", help="Connect to ppcoind")

parser.add_option("-R", "--listreceived", dest="listreceived", action="store_true", default=False, help="List totals received by account/label")

parser.add_option("-r", "--hashrate", dest="hashrate", help="Hashes/sec from external miners, or blocksperday for primecoin")

parser.add_option("-S", "--skeincoin", action="store_const", const="skeincoin", dest="coin", default="bitcoin", help="Connect to skeincoind")

parser.add_option("-s", "--sendto", dest="sendto", help="Send coins to this address, followed by the amount")

parser.add_option("-T", "--TjcoinV2", action="store_const", const="TjcoinV2", dest="coin", default="bitcoin", help="Connect to Tjcoind")

parser.add_option("-t", "--transactions", dest="transactions", action="store_true", default=False, help="List recent transactions")

parser.add_option("-U", "--universalmolecule", action="store_const", const="universalmolecule", dest="coin", default="bitcoin", help="Connect to universalmoleculed")

parser.add_option("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local bitcoind")

parser.add_option("-V", "--virtacoin", action="store_const", const="virtacoin", dest="coin", default="bitcoin", help="Connect to virtacoind")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False, help="Print more detailed info")

parser.add_option("-W", "--watts", dest="watts", help="Power usage of miners for profitability calculation")

parser.add_option("-w", "--kwh-price", dest="kwhprice", help="kWh price in EUR for profitability calculation")

parser.add_option("-X", "--cryptonite", action="store_const", const="cryptonite", dest="coin", default="bitcoin", help="Connect to cryptonited")

parser.add_option("-x", "--dirac", action="store_const", const="dirac", dest="coin", default="bitcoin", help="Connect to diracd")

parser.add_option("-y", "--vertcoin", action="store_const", const="vertcoin", dest="coin", default="bitcoin", help="Connect to vertcoind")

(options, args) = parser.parse_args()

coin = options.coin

# coin-dependent constants
currency = {
    "AuroraCoin": "AUR",
    "bitcoin": "BTC",
    "blakebitcoin": "BBTC",
    "blakecoin": "BLC",
    "chncoin": "CNC",
    "cryptonite": "XCN",
    "darkcoin": "DRK",
    "dirac": "XDQ",
    "dogecoin": "DOGE",
    "ecoin": "ECN",
    "electron": "ELT",
    "GroestlCoin": "GRS",
    "litecoin": "LTC",
    "maxcoin": "MAX",
    "namecoin": "NMC",
    "photon": "PHO",
    "ppcoin": "PPC",
    "primecoin": "XPM",
    "primio": "Primio",
    "riecoin": "RIC",
    "ShibeCoin": "Shibe",
    "skeincoin": "SKC",
    "SlothCoin": "Sloth",
    "TjcoinV2": "TJC",
    "universalmolecule": "UMO",
    "vertcoin": "VTC",
    "virtacoin": "VTA",
}

# 0 means no block reward halving
blockhalve = {
    "AuroraCoin": 420000,
    "bitcoin": 210000,
    "blakebitcoin": 210000,
    "chncoin": 2628000,
    "darkcoin": 0,
    "ecoin": 0,
    "litecoin": 840000,
    "maxcoin": 1051200,
    "namecoin": 0,
    "primio": 100000,
    "riecoin": 840000,
    "ShibeCoin": 0,
    "skeincoin": 262800,
    "SlothCoin": 100000,
    "TjcoinV2": 840000,
    "universalmolecule": 0,
    "vertcoin": 840000,
    "virtacoin": 10080,
}

blocksperhour = {
    "AuroraCoin": 6,
    "bitcoin": 6,
    "blakebitcoin": 24,
    "blakecoin": 20,
    "chncoin": 60,
    "cryptonite": 60,
    "darkcoin": 24,
    "dirac": 20,
    "dogecoin": 60,
    "ecoin": 60,
    "electron": 60,
    "GroestlCoin": 60,
    "litecoin": 24,
    "maxcoin": 120,
    "namecoin": 6,
    "photon": 20,
    "primecoin": 60,
    "primio": 12,
    "riecoin": 24,
    "ShibeCoin": 60,
    "skeincoin": 30,
    "SlothCoin": 24,
    "TjcoinV2": 24,
    "universalmolecule": 30,
    "vertcoin": 24,
    "virtacoin": 60,
}

# 0 means dynamic difficulty adjustment without fixed intervals
adjustblocks = {
    "AuroraCoin": 8,
    "bitcoin": 2016,
    "blakebitcoin": 8064,
    "blakecoin": 20,
    "chncoin": 0,
    "cryptonite": 0,
    "darkcoin": 0,
    "dirac": 20,
    "dogecoin": 0,
    "ecoin": 100,
    "electron": 0, # ?
    "GroestlCoin": 0,
    "litecoin": 2016,
    "maxcoin": 0,
    "namecoin": 2016,
    "photon": 20,
    "ppcoin": 0,
    "primecoin": 0,
    "primio": 12,
    "riecoin": 288,
    "ShibeCoin": 0,
    "skeincoin": 0,
    "SlothCoin": 2,
    "TjcoinV2": 336,
    "universalmolecule": 20,
    "vertcoin": 0,
    "virtacoin": 0,
}

# For coins with regular block halving
initcoins = {
    "AuroraCoin": 25,
    "bitcoin": 50,
    "blakecoin": 50,
    "blakebitcoin": 50,
    "chncoin": 88,
    "ecoin": 700,
    "maxcoin": 48,
    "namecoin": 50,
    "litecoin": 50,
    "photon": 32768,
    "primio": 50,
    "riecoin": 50,
    "ShibeCoin": 0, # Not meaningful for mostly proof of stake coin
    "skeincoin": 32,
    "SlothCoin": 500000,
    "TjcoinV2": 50,
    "universalmolecule": 0.1, # Minimum
    "vertcoin": 50,
    "virtacoin": 8000,
}

# (list of block limits, list of fixed rewards for those intervals)
reward_stairs = {
    "dirac": ([0, 43201, 744001, 1448001, 2145601, 2846401],
              [8.0, 1.25, 0.75, 0.5, 0.25, 0.01]),
    "dogecoin": ([0, 100000, 200000, 300000, 400000, 500000, 600000], 
                 [500000, 250000, 125000, 62500, 31250, 15625, 10000]),
    "electron": ([0, 525600],
                 [20, 10]),
}

rpcport = {
    "AuroraCoin": "12341",
    "bitcoin": "8332",
    "blakebitcoin": "243",
    "blakecoin": "8772",
    "chncoin": "8108",
    "cryptonite": "8252",
    "darkcoin": "9998",
    "dirac": "74532",
    "dogecoin": "22555",
    "ecoin": "10444",
    "electron": "6852", 
    "GroestlCoin": "1441",
    "litecoin": "9332",
    "maxcoin": "8669",
    "namecoin": "8332",
    "photon": "74532",
    "ppcoin": "9902",
    "primecoin": "9912",
    "primio": "1218",
    "riecoin": "28332",
    "ShibeCoin": "18812",
    "skeincoin": "21230",
    "SlothCoin": "5108",
    "TjcoinV2": "9178",
    "universalmolecule": "19738",
    "vertcoin": "5888",
    "virtacoin": "22815",
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

if options.verbose:
    keys = info.keys()
else:
    # Primecoin does not provide difficulty in getinfo, only separately
    keys = ["balance", "testnet"]

if options.diff:
    diff = float(options.diff)
else:
    diff = s.getdifficulty()

    # Hybrid PoW / PoS
    if type(diff) == dict:
        diff = diff['proof-of-work']

output = []
for key in keys:
    output.append([key, str(info[key])])

# Primecoin above
if "difficulty" not in keys:
    output.append(["difficulty", str(diff)])

if options.hashrate:
    hashrate = float(options.hashrate)
    # No point in printing this, if supplied manually
else:
    if coin == "primecoin":
        hashrate = s.getmininginfo()["blocksperday"]

        if options.verbose:
            output.append(["blocksperday", str(hashrate)])
    elif coin == "litecoin":
        # Mining was removed from the client in 0.8
        hashrate = 0
    else:
        hashrate = s.gethashespersec()
        if options.verbose:
            output.append(["hashespersec", str(hashrate)])

blocks = info["blocks"]

if options.verbose:
    output.append(["block reward", str(blockreward(coin, diff, blocks)) + " " + currency[coin]])

prettyprint(output)

if options.verbose:
    own_share(coin, blocks, info)

output = []

if hashrate > 0 and coin != "riecoin":
    if coin == "primecoin":
        time = 86400. / hashrate
    elif coin == "cryptonite":
        # Guess based on current network hashrate and difficulty
        time = diff * 2**20 / hashrate
    else:
        time = diff * 2**32 / hashrate

    tp = timeprint(time)
    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])
    
    coinsperday = blockreward(coin, diff, blocks) / time * 86400

    output.append(["Average payout", str(coinsperday) + " " + currency[coin] + "/day"])

    fiatprice = coin_price(coin)    

    if fiatprice > 0:

        fiatpay = coinsperday * fiatprice

        output.append(["1 " + currency[coin], str(fiatprice) + " EUR"])
        output.append(["Fiat payout", str(fiatpay) + " " + "EUR/day"])

        if options.watts and options.kwhprice:
            watts = float(options.watts)
            kwhprice = float(options.kwhprice)
            cost = kwhprice * watts / 1000 * 24
        
            if cost > 0:
                pratio = fiatpay / cost
                
                if pratio > 2:
                    emo = ":D"
                elif pratio > 1:
                    emo = ":)"
                else:
                    emo = ":("

                output.append(["Payout/cost", str(pratio) + " " + emo])
                output.append(["Net profit", str(fiatpay - cost) + " EUR/day"])

if adjustblocks[coin] > 0:
    time = (adjustblocks[coin] - blocks % adjustblocks[coin]) / float(blocksperhour[coin]) * 3600
    tp = timeprint(time)
    output.append(["\nNext difficulty expected in", str(tp[0]) + " " + tp[1]])

errors = info["errors"]
if len(errors) > 0:
    output.append(["\nError", errors])

if len(output) > 0:
    prettyprint(output)
