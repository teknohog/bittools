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

# https://github.com/joshmarshall/jsonrpclib
from jsonrpclib import Server

from sys import exit
from optparse import OptionParser
import re
from math import ceil, exp
from time import ctime

from bittools import *

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

def lastreward(blocks):
    # Use the last block reward as an estimate, need to check for PoW,
    # should work for several coins. Don't wind back too much in case
    # of PoS only.
    for i in range(blocks, blocks - 1000, -1):
        b = s.getblock(s.getblockhash(i))
        if b["flags"] == "proof-of-work":
            return b["mint"]
    return 0

def blockreward(coin, diff, blocks):
    if coin == "ppcoin":
        # https://bitcointalk.org/index.php?topic=101820.msg1118737#msg1118737
        # "The block reward for a work block is sqrt(sqrt(9999^4 /
        # difficulty)), rounded down to the next cent boundary."
        return int(999900. / diff**0.25) / 100.
    elif coin == "gapcoin":
        return exp_decay(diff, blocks, 420000)
    elif coin == "primecoin":
        # block reward = 999 / diff**2, likewise floored to cent
        return int(99900. / diff**2) / 100.
    elif coin in ["blakecoin", "photon"]:
        return initcoins[coin] + round((blocks * diff * 256)**0.5) * 1e-8
    elif coin == "dash":
        return max(2222222. / (((diff + 2600.)/9.)**2), 5.0)
    elif coin == "groestlcoin":
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
    elif coin == "Vcash":
        # From reward.cpp until block 325000
        #return exp_decay(128, blocks, 50000, 5./6.)
        return lastreward(blocks)
    elif coin == "zcash":
        # Linear ramp-up for the first 20000 blocks, then basic halving
        return min(blocks/2e4, 1) * exp_decay(initcoins[coin], blocks, blockhalve[coin])
    else:
        return exp_decay(initcoins[coin], blocks, blockhalve[coin])

# Extended precision float encoding for Cryptonite
def ep_enc(x):
    return '%.10fep' % x

def ep_dec(s):
    return float(s.rstrip('ep'))

def total_supply(coin, blocks, info):
    total = 0
    final_total = 0

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

    return (total, final_total)

def own_share(coin, blocks, info, fiatprice, basecur):
    printout = []

    (total, final_total) = total_supply(coin, blocks, info)
    
    if info["balance"] > 0:
        if total > 0:
            share = info["balance"] / total
            printout.append([str(share * 100), str(int(round(1/share))) + " of all current " + currency[coin]])

        if final_total > 0:
            share = info["balance"] / final_total
            printout.append([str(share * 100), str(int(round(1/share))) + " of all " + currency[coin] + " ever"])

    fiat_balance = fiatprice * info["balance"]
            
    if len(printout) > 0 or fiat_balance > 0:
        print("\nYour balance represents about")
        
        if fiat_balance > 0:
            print("%f %s (1 %s = %f %s)" % (fiat_balance, basecur, currency[coin], fiatprice, basecur))

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

def exportkeys():
            
    from os import unlink
        
    l = []

    try:
        # dumpwallet is the best method if available, as it should
        # give the complete list of keys. Vcash has a different format
        # -- maybe other coins use csv too?
        
        if coin == "Vcash":
            dumpfile = os.path.expanduser("~/.Vcash/data/wallet.csv")
            s.dumpwallet(dumpfile)
            keydump = ReadLines(dumpfile)[1:]
            unlink(dumpfile)
            
            for line in keydump:
                kat = line.split(",") # Key,Address,Type
                if len(kat) == 3:
                    # Could also check for "reserve" addresses which
                    # might not be essential to save
                    
                    if kat[2].strip() == "label":
                        account = s.getaccount(kat[1])
                    else:
                        account = ""

                    l.append([kat[0], account])

        else:
            dumpfile = os.path.expanduser("~/." + coin + "/walletdump.txt")
            s.dumpwallet(dumpfile)
            keydump = ReadLines(dumpfile)
            unlink(dumpfile)

            for line in keydump:
                # Check for valid lines first, as they have addr=... in the end
                m = re.match('.*addr=(\S.*)$', line)
                if m is None:
                    continue

                m = re.match('.*label=(\S.*)\s+#.*', line)
                if m is None:
                    account = ""
                else:
                    account = m.group(1)

                privkey = line.split()[0]
                    
                l.append([privkey, account])

    except:
        print("No dumpwallet method available, list of keys may be incomplete")
        
        # Generate addresses are not available via accounts, even though
        # they are listed under the "" account. So this way should get us
        # all possible addresses...
        
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

        # EXCL: "Accounting API is deprecated and will be removed in future."
        try:
            accounts = s.listaccounts()

            for acc in accounts:
                addresses = s.getaddressesbyaccount(acc)
                for addr in addresses:
                    privkey = s.dumpprivkey(addr)
                    item = [privkey, acc]
            
                    if item not in l:
                        l.append(item)
        except:
            print("Warning: missing listaccounts method, list of keys may be incomplete\n")

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

def listtransactions(args):

    # Optional selection by account and number of transactions there.
    if len(args) == 1:
        trans = s.listtransactions(args[0])
    elif len(args) == 2:
        trans = s.listtransactions(args[0], int(args[1]))
    else:
        trans = s.listtransactions()
        
    if len(trans) > 0:
        output = []
        for item in trans:
            unconfirmed = item["confirmations"] < 1 or item["category"] == "immature"
            if "address" in item.keys():
                address = item["address"]
            else:
                address = ""
            output.append([ctime(item["time"]), item["category"][0].upper(), item["account"], str(item["amount"]), unconfirmed * "*", options.verbose * address, options.verbose * str(item["confirmations"])])

        prettyprint(output)
        
def send(address, amount, new_txfee):
    # Double check the amount and address -- the command line may be
    # split over two lines, making the amount less obvious

    # Set transfer fee for this send only
    default_txfee = s.getinfo()["paytxfee"]
    if new_txfee >= 0:
        txfee = new_txfee
        s.settxfee(txfee)
    else:
        txfee = default_txfee
        
    print("About to send " + currency[coin] + " " + str(amount) + " to " + address + " with txfee " + str(txfee))

    # Warn of potential dupes; sends show up with empty account name
    trans = s.listtransactions('')
    if len(trans) > 0:
        for item in trans:
            if "address" in item.keys() and address == item["address"]:
                if coin == "cryptonite":
                    item["amount"] = ep_dec(item["amount"])

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

    # Reset the daemon's default txfee, in any case
    if new_txfee >= 0:
        s.settxfee(default_txfee)
        
def meandiff2(coin):
    # Alternative for testing: use blockchain data instead of saved
    # logfiles. A nice idea but notably slower :-/
    ndata = 10
    blockint = blocksperhour[coin]
    data = []

    # Start from top block and work backwards
    i = info["blocks"]
    for n in range(ndata):
        # PoW only coins for now, see lastreward() for PoW/PoS flags
        b = s.getblock(s.getblockhash(i))
        data.append([b["time"], b["difficulty"]])
        i -= blockint

    if len(data) >= ndata/2:
        ab = linear_regression(data)

        # Estimate a current diff
        return ab[0] + ab[1] * time()
    else:
        return 0
        
parser = OptionParser()

parser.add_option("-A", "--listaccounts", dest="listaccounts", action="store_true", default=False, help="List accounts with balances")

parser.add_option("-a", "--AuroraCoin", action="store_const", const="AuroraCoin", dest="coin", default="bitcoin", help="Connect to AuroraCoind")

parser.add_option("-B", "--blakecoin", action="store_const", const="blakecoin", dest="coin", default="bitcoin", help="Connect to blakecoind")

parser.add_option("--backupwallet", dest="backupwallet", help="Backup wallet to the given file; use a full pathname")

parser.add_option("-b", "--byaccount", dest="byaccount", help="List addresses by the given account")

parser.add_option("--basecur", default = "EUR", help="Base currency for coin and kWh prices, default EUR")

parser.add_option("--bitcoin", action="store_const", const="bitcoin", dest="coin", default="bitcoin", help="Connect to bitcoind")

parser.add_option("-c", "--chncoin", action="store_const", const="chncoin", dest="coin", default="bitcoin", help="Connect to chncoind")

parser.add_option("-d", "--difficulty", dest="diff", type = float, help="Set difficulty for mining calculator")

parser.add_option("-D", "--dogecoin", action="store_const", const="dogecoin", dest="coin", default="bitcoin", help="Connect to dogecoind")

parser.add_option("--ecoin", action="store_const", const="ecoin", dest="coin", default="bitcoin", help="Connect to ecoind")

parser.add_option("-E", "--electron", action="store_const", const="electron", dest="coin", default="bitcoin", help="Connect to electrond")

parser.add_option("-e", "--exportkeys", dest="export", action="store_true", default=False, help="Export all private keys, along with account names")

parser.add_option("-F", "--gapcoin", action="store_const", const="gapcoin", dest="coin", default="bitcoin", help="Connect to gapcoind")

parser.add_option("-G", "--groestlcoin", action="store_const", const="groestlcoin", dest="coin", default="bitcoin", help="Connect to groestlcoind")

parser.add_option("-g", "--ShibeCoin", action="store_const", const="ShibeCoin", dest="coin", default="bitcoin", help="Connect to ShibeCoind")

parser.add_option("-H", "--photon", action="store_const", const="photon", dest="coin", default="bitcoin", help="Connect to photond")

parser.add_option("-I", "--riecoin", action="store_const", const="riecoin", dest="coin", default="bitcoin", help="Connect to riecoind")

parser.add_option("-i", "--importkeys", dest="importfile", help="Import private keys from file (see exportkeys output for formatting)")

parser.add_option("-J", "--Vcash", action="store_const", const="Vcash", dest="coin", default="bitcoin", help="Connect to Vcashd")

parser.add_option("-j", "--primio", action="store_const", const="primio", dest="coin", default="bitcoin", help="Connect to primiod")

parser.add_option("-K", "--dash", action="store_const", const="dash", dest="coin", default="bitcoin", help="Connect to dashd")

parser.add_option("-k", "--blakebitcoin", action="store_const", const="blakebitcoin", dest="coin", default="bitcoin", help="Connect to blakebitcoind")

parser.add_option("-L", "--Slothcoin", action="store_const", const="Slothcoin", dest="coin", default="bitcoin", help="Connect to Slothcoind")

parser.add_option("-l", "--litecoin", action="store_const", const="litecoin", dest="coin", default="bitcoin", help="Connect to litecoind")

parser.add_option("-N", "--newaddress", dest="newaddress", action="store_true", default=False, help="Get new address, optionally for the given account")

parser.add_option("-m", "--maxcoin", action="store_const", const="maxcoin", dest="coin", default="bitcoin", help="Connect to maxcoind")

parser.add_option("-n", "--namecoin", action="store_const", const="namecoin", dest="coin", default="bitcoin", help="Connect to namecoind")

parser.add_option("--peers", action="store_true", default=False, help="List connections")

parser.add_option("-P", "--primecoin", action="store_const", const="primecoin", dest="coin", default="bitcoin", help="Connect to primecoind")

parser.add_option("-p", "--ppcoin", action="store_const", const="ppcoin", dest="coin", default="bitcoin", help="Connect to ppcoind")

parser.add_option("-R", "--listreceived", dest="listreceived", action="store_true", default=False, help="List totals received by account/label")

parser.add_option("-r", "--hashrate", dest="hashrate", type = float, help="Hashes/sec from external miners, or blocksperday for primecoin")

parser.add_option("-S", "--skeincoin", action="store_const", const="skeincoin", dest="coin", default="bitcoin", help="Connect to skeincoind")

parser.add_option("-s", "--sendto", dest="sendto", help="Send coins to this address, followed by the amount")

parser.add_option("-T", "--TjcoinV2", action="store_const", const="TjcoinV2", dest="coin", default="bitcoin", help="Connect to Tjcoind")

parser.add_option("-t", "--transactions", dest="transactions", action="store_true", default=False, help="List recent transactions, optionally filtered by account name (e.g. '' for generates), and optional number (default 10)")

parser.add_option("--txfee", dest="txfee", type = float, default = -1, help="Transaction fee for this send, instead of the daemon default")

parser.add_option("-U", "--universalmolecule", action="store_const", const="universalmolecule", dest="coin", default="bitcoin", help="Connect to universalmoleculed")

parser.add_option("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local bitcoind")

parser.add_option("-V", "--virtacoin", action="store_const", const="virtacoin", dest="coin", default="bitcoin", help="Connect to virtacoind")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False, help="Print more detailed info")

parser.add_option("-W", "--watts", dest="watts", type = float, help="Power usage of miners for profitability calculation")

parser.add_option("-w", "--kwh-price", dest="kwhprice", type = float, help="kWh price for profitability calculation")

parser.add_option("-X", "--cryptonite", action="store_const", const="cryptonite", dest="coin", default="bitcoin", help="Connect to cryptonited")

parser.add_option("-x", "--dirac", action="store_const", const="dirac", dest="coin", default="bitcoin", help="Connect to diracd")

parser.add_option("-Y", "--lithium", action="store_const", const="lithium", dest="coin", default="bitcoin", help="Connect to lithiumd")

parser.add_option("-y", "--vertcoin", action="store_const", const="vertcoin", dest="coin", default="bitcoin", help="Connect to vertcoind")

parser.add_option("-z", "--ExclusiveCoin", action="store_const", const="ExclusiveCoin", dest="coin", default="bitcoin", help="Connect to ExclusiveCoind")

parser.add_option("-Z", "--zcash", action="store_const", const="zcash", dest="coin", default="bitcoin", help="Connect to zcashd")

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
    "dash": "DASH",
    "dirac": "XDQ",
    "dogecoin": "DOGE",
    "ecoin": "ECN",
    "electron": "ELT",
    "ExclusiveCoin": "EXCL",
    "groestlcoin": "GRS",
    "gapcoin": "GAP",
    "litecoin": "LTC",
    "lithium": "LIT",
    "maxcoin": "MAX",
    "namecoin": "NMC",
    "photon": "PHO",
    "ppcoin": "PPC",
    "primecoin": "XPM",
    "primio": "Primio",
    "riecoin": "RIC",
    "ShibeCoin": "Shibe",
    "skeincoin": "SKC",
    "Slothcoin": "Sloth",
    "TjcoinV2": "TJC",
    "universalmolecule": "UMO",
    "Vcash": "XVC",
    "vertcoin": "VTC",
    "virtacoin": "VTA",
    "zcash": "ZEC",
}

# 0 means no block reward halving
blockhalve = {
    "AuroraCoin": 420000,
    "bitcoin": 210000,
    "blakebitcoin": 210000,
    "chncoin": 2628000,
    "dash": 0,
    "ecoin": 0,
    "litecoin": 840000,
    "lithium": 0,
    "maxcoin": 1051200,
    "namecoin": 0,
    "primio": 100000,
    "riecoin": 840000,
    "ShibeCoin": 0,
    "skeincoin": 262800,
    "Slothcoin": 100000,
    "TjcoinV2": 840000,
    "universalmolecule": 0,
    "vertcoin": 840000,
    "virtacoin": 10080,
    "zcash": 840000,
}

blocksperhour = {
    "AuroraCoin": 6,
    "bitcoin": 6,
    "blakebitcoin": 24,
    "blakecoin": 20,
    "chncoin": 60,
    "cryptonite": 60,
    "dash": 24,
    "dirac": 20,
    "dogecoin": 60,
    "ecoin": 60,
    "electron": 60,
    "ExclusiveCoin": 90,
    "groestlcoin": 60,
    "gapcoin": 24,
    "litecoin": 24,
    "lithium": 20,
    "maxcoin": 120,
    "namecoin": 6,
    "photon": 20,
    "primecoin": 60,
    "primio": 12,
    "riecoin": 24,
    "ShibeCoin": 60,
    "skeincoin": 30,
    "Slothcoin": 24,
    "TjcoinV2": 24,
    "universalmolecule": 30,
    "Vcash": 25, # Mean?
    "vertcoin": 24,
    "virtacoin": 60,
    "zcash": 24,
}

# 0 means dynamic difficulty adjustment without fixed intervals
adjustblocks = {
    "AuroraCoin": 8,
    "bitcoin": 2016,
    "blakebitcoin": 8064,
    "blakecoin": 20,
    "chncoin": 0,
    "cryptonite": 0,
    "dash": 0,
    "dirac": 20,
    "dogecoin": 0,
    "ecoin": 100,
    "electron": 0, # ?
    "ExclusiveCoin": 0,
    "gapcoin": 0,
    "groestlcoin": 0,
    "litecoin": 2016,
    "lithium": 20,
    "maxcoin": 0,
    "namecoin": 2016,
    "photon": 20,
    "ppcoin": 0,
    "primecoin": 0,
    "primio": 12,
    "riecoin": 288,
    "ShibeCoin": 0,
    "skeincoin": 0,
    "Slothcoin": 2,
    "TjcoinV2": 336,
    "universalmolecule": 20,
    "Vcash": 0, # ?4
    "vertcoin": 0,
    "virtacoin": 0,
    "zcash": 0,
}

# For coins with regular block halving
initcoins = {
    "AuroraCoin": 25,
    "bitcoin": 50,
    "blakecoin": 25,
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
    "Slothcoin": 500000,
    "TjcoinV2": 50,
    "universalmolecule": 0.1, # Minimum
    "vertcoin": 50,
    "virtacoin": 8000,
    "zcash": 12.5, # after first 2e5 blocks -- use for total_supply approx
}

# (list of block limits, list of fixed rewards for those intervals)
reward_stairs = {
    "dirac": ([0, 43201, 744001, 1448001, 2145601, 2846401],
              [8.0, 1.25, 0.75, 0.5, 0.25, 0.01]),
    "dogecoin": ([0, 100000, 200000, 300000, 400000, 500000, 600000], 
                 [500000, 250000, 125000, 62500, 31250, 15625, 10000]),
    "electron": ([0, 525600, 1051200],
                 [20, 10, 5]),
    "ExclusiveCoin": ([0, 1120706], [8, 4]),
    "lithium": ([0, 2000, 175000, 350000, 525000, 650000, 800000, 975000],
                [0.48, 48, 24, 12, 6, 3, 1.5, 1]),
}

rpcport = {
    "AuroraCoin": "12341",
    "bitcoin": "8332",
    "blakebitcoin": "243",
    "blakecoin": "8772",
    "chncoin": "8108",
    "cryptonite": "8252",
    "dash": "9998",
    "dirac": "74532",
    "dogecoin": "22555",
    "ecoin": "10444",
    "electron": "6852", 
    "ExclusiveCoin": "22621",
    "groestlcoin": "1441",
    "gapcoin": "31397",
    "litecoin": "9332",
    "lithium": "12000",
    "maxcoin": "8669",
    "namecoin": "8332",
    "photon": "74532",
    "ppcoin": "9902",
    "primecoin": "9912",
    "primio": "1218",
    "riecoin": "28332",
    "ShibeCoin": "18812",
    "skeincoin": "21230",
    "Slothcoin": "5108",
    "TjcoinV2": "9178",
    "universalmolecule": "19738",
    "Vcash": "9195",
    "vertcoin": "5888",
    "virtacoin": "22815",
    "zcash": "8232",
}

if len(options.url) > 0:
    url = options.url
elif coin == "Vcash":
    # No login credentials needed
    url = "http://localhost:9195/"
else:
    configfile = "~/." + coin + "/" + coin + ".conf"

    settings = parse_config(configfile)

    # Use default port numbers
    if not 'rpcport' in settings.keys():
        settings['rpcport'] = rpcport[coin]

    url = "http://" + settings['rpcuser'] + ":" + settings['rpcpassword'] + "@127.0.0.1:" + settings['rpcport'] + "/"

s = Server(url)

if options.byaccount:
    if coin == "Vcash":
        # Only one address; at least dumpwallet will give them all
        print(s.getaccountaddress(options.byaccount))
    else:
        for addr in s.getaddressesbyaccount(options.byaccount):
            print(addr)
    exit()

if options.export:
    exportkeys()
    exit()

if options.importfile:
    importkeys(options.importfile)
    exit()

if options.listaccounts:
    listaccounts()
    exit()

if options.listreceived:
    listreceived()
    exit()

if options.newaddress:
    print(s.getnewaddress(args[0]))
    exit()

if options.sendto:
    send(options.sendto, float(args[0]), options.txfee)
    exit()

if options.transactions:
    listtransactions(args)
    exit()

if options.backupwallet:
    s.backupwallet(options.backupwallet)
    exit()

if options.peers:
    # The ip addresses contain occasional dupes
    peers = s.getpeerinfo()
    peer_ips = set()
    for p in peers:
        addr = p["addr"].split(":")[0] 
        peer_ips.add(addr)
    for ip in peer_ips:
        print(ip)
    exit()
    
info = s.getinfo()

if options.verbose:
    keys = info.keys()
elif coin == "Vcash":
    # No testnet in info
    keys = ["balance"]
else:
    # Primecoin does not provide difficulty in getinfo, only separately
    keys = ["balance", "testnet"]

if coin == "cryptonite":
    info["balance"] = ep_dec(info["balance"])
    
if options.diff:
    diff = options.diff
else:
    diff = s.getdifficulty()

    # Hybrid PoW / PoS
    if type(diff) == dict:
        diff = diff['proof-of-work']
        
        # Print PoW diff only for simpler parsing on external scripts
        info['difficulty'] = diff

    md = meandiff(coin, diff)
    if md > 0:
        keys.append('meandiff')
        info['meandiff'] = md
    
output = []
for key in keys:
    output.append([key, str(info[key])])

# Primecoin above
if "difficulty" not in keys:
    output.append(["difficulty", str(diff)])

if options.hashrate:
    hashrate = options.hashrate
    # No point in printing this, if supplied manually
else:
    if coin == "primecoin":
        hashrate = s.getmininginfo()["blocksperday"]
        if options.verbose:
            output.append(["blocksperday", str(hashrate)])
    elif coin == "gapcoin":
        hashrate = s.getprimespersec()
    elif coin in ["bitcoin", "dogecoin", "litecoin", "ExclusiveCoin", "zcash"]:
        # Litecoin: Mining was removed from the client in 0.8
        # EXCL: not available
        # Bitcoin: removed in 0.11.0
        # zcash: no info available despite mining
        hashrate = 0
    else:
        try:
            hashrate = s.getmininginfo()["hashespersec"]
        except:
            hashrate = s.gethashespersec()

try:
    networkhashrate = s.getmininginfo()["networkhashps"]
except:
    networkhashrate = 0
            
if coin != "primecoin" and options.verbose:
    output.append(["hashespersec", str(hashrate)])

    if networkhashrate > 0:
        output.append(["networkhashrate", str(networkhashrate)])
        
blocks = info["blocks"]

if options.verbose:
    output.append(["block reward", str(blockreward(coin, diff, blocks)) + " " + currency[coin]])

prettyprint(output)

if options.verbose:
    fiatprice = coin_price(currency[coin], options.basecur)
    
    own_share(coin, blocks, info, fiatprice, options.basecur)

    if networkhashrate > 0 and hashrate > 0:
        share = hashrate / networkhashrate
        print("\nYour hashrate represents about " + str(share * 100) + " % or 1/" + str(int(round(1/share))) + " of the network")
else:
    # Argument for profit() which will call coin_price() again if need be
    fiatprice = 0
        
output = []

if hashrate > 0 and coin != "riecoin":
    if 'meandiff' in info.keys() and not options.diff:
        diff = info['meandiff']
    
    if coin == "primecoin":
        blocktime = 86400. / hashrate
    elif coin == "cryptonite":
        # Guess based on current network hashrate and difficulty
        blocktime = diff * 2**20 / hashrate
    elif coin == "gapcoin":
        # From http://coinia.net/gapcoin/calc.php
        blocktime = exp(diff) / hashrate
    elif coin == "zcash":
        # Guess based on networkhashrate comparisons
        blocktime = diff * 2**13 / hashrate
    else:
        blocktime = diff * 2**32 / hashrate

    output += profit(blocktime, blockreward(coin, diff, blocks), currency[options.coin], options.watts, options.kwhprice, fiatprice, options.basecur)

if adjustblocks[coin] > 0:
    adjtime = (adjustblocks[coin] - blocks % adjustblocks[coin]) / float(blocksperhour[coin]) * 3600
    tp = timeprint(adjtime)
    output.append(["\nNext difficulty expected in", str(tp[0]) + " " + tp[1]])

if "errors" in info and len(info["errors"]) > 0:
    output.append(["\nError", info["errors"]])

if len(output) > 0:
    prettyprint(output)
