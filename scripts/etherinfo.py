#!/usr/bin/env python

# by teknohog 2016-01-03

# Rudimentary access to Ethereum json-rpc

# https://github.com/ethereum/wiki/wiki/JSON-RPC

from jsonrpclib import Server

from sys import exit

from bittools import *

def WriteFile(filename, content):
    File = open(filename, "w")
    File.write(content)
    File.close()

# Use plain decimal for balances here, as 1 ether = 1e18 wei
def tohexwei(x):
    return hex(int(x * 1e18))

def fromhexwei(x):
    return 1e-18 * int(x, 16)

def get_balance(addr):
    hwbal = daemon.eth_getBalance(addr, "latest")
    return fromhexwei(hwbal)

def send(fromaddr, toaddr, amount):
    print("About to send " + str(amount) + " " + currency[options.coin] + " from " + fromaddr + " to " + toaddr)

    c_input = input("OK (yes/no)? ")
    if c_input != "yes":
        exit()
    
    # Save the balance file after sending. The balance won't be
    # updated immediately, so estimate this -- will be less due to
    # transfer fees and whatnot.
    bal = get_balance(fromaddr) - amount - 0.001

    txdata = daemon.eth_sendTransaction({"from": fromaddr, "to": toaddr, "value": tohexwei(amount)})

    print("Transaction sent: " + txdata)
    
    balfile = os.path.expanduser(basedir + "/keystore/" + fromaddr + ".balance")
    # Newline makes a manual cat cleaner for the shell
    WriteFile(balfile, str(bal) + "\n")
    
def lastsend(fromaddr, toaddr, fraction, minsend):
    balfile = os.path.expanduser(basedir + "/keystore/" + fromaddr + ".balance")
    if os.path.exists(balfile):
        oldbal = float(ReadLines(balfile)[0].strip())
    else:
        oldbal = 0
    
    newbal = get_balance(fromaddr)
    amount = (newbal - oldbal) * fraction
    
    if amount >= minsend:
        send(fromaddr, toaddr, amount)
    else:
        print("Not enough new funds received: got " + str(newbal - oldbal) + ", need " + str(minsend / fraction))

def dictprint(a):
    # prettyprint for dictionaries
    maxwidth = max(map(len, a))
    for key in a:
        # Assume keys are strings
        print(key + (maxwidth - len(key) + 1) * " " + str(a[key]))

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--account_id", "-a", type = int, default = -1, help = "Index of local account/address, starting from 0 = coinbase, in the order shown in balances")

parser.add_argument("--basecur", default = "EUR", help="Base currency for coin and kWh prices, default EUR")

parser.add_argument("-c", "--classic", action="store_const", const="ethereum-classic", dest="coin", default="ethereum", help="Connect to Ethereum Classic")

parser.add_argument("-d", "--diff", type=float, default = 0, help="Set difficulty manually for mining estimation")

parser.add_argument("--fraction", "-f", type = float, default = 0.5, help = "Lastsend fraction, default %(default)f")

parser.add_argument("--lastsend", "-l", help = "Send a fraction (-f) of new income (-a) to this address")

parser.add_argument("--minsend", "-m", type = float, default = 1, help = "Lower limit for lastsend, default %(default)f ETH")

parser.add_argument("-r", "--hashrate", dest="hashrate", type=float, default = 0, help="Hashes/sec from external miners")

parser.add_argument("--sendto", "-s", nargs = 2, help = "Send toaddress amount in ETH. The account must be unlocked.")

parser.add_argument("-u", "--url", dest="url", default="http://localhost:8545", help="Connect to a different URL, instead of your local Ethereum daemon")

parser.add_argument("-v", "--verbose", action = "store_true")

parser.add_argument("-W", "--watts", dest="watts", type=float, help="Power usage of miners for profitability calculation")

parser.add_argument("-w", "--kwhprice", dest="kwhprice", type=float, help="kWh price for profitability calculation")

options = parser.parse_args()

daemon = Server(options.url)

info = {"hashrate": float(int(daemon.eth_hashrate(), 16)),
        "balances": list(map(get_balance, daemon.eth_accounts())),
        "blocks": int(daemon.eth_blockNumber(), 16),
        "difficulty": float(int(daemon.eth_getBlockByNumber("latest", False)["difficulty"], 16)),
        "peers": int(daemon.net_peerCount(), 16),
        }

info["total balance"] = sum(info["balances"])

if options.coin == "ethereum-classic":
    basedir = "~/.ethereum-classic/mainnet"
    info["blockreward"] = exp_decay(5, info["blocks"], 5000000, 0.8)
else:
    basedir = "~/.ethereum"
    info["blockreward"] = 3

if options.account_id > -1:
    aid = options.account_id
    fromaddr = daemon.eth_accounts()[aid]

    if options.sendto:
        toaddr = options.sendto[0]
        amount = float(options.sendto[1])

        send(fromaddr, toaddr, amount)
        exit()

    elif options.lastsend:
        lastsend(fromaddr, options.lastsend, options.fraction, options.minsend)
        exit()

    else:
        # Just add that address into general info
        info["account " + str(aid) + " address"] = fromaddr
        
md = meandiff("ethereum", info["difficulty"])
if md > 0:
    info["meandiff"] = md

if options.hashrate:
    info["hashrate"] = options.hashrate
    
dictprint(info)

if options.verbose:
    fiatprice = coin_price(options.coin, options.basecur)

    if fiatprice > 0:
        print("\nYour balance represents about")
        print("%f %s (1 %s = %f %s)" % (fiatprice * info["total balance"], options.basecur, currency[options.coin], fiatprice, options.basecur))
else:
    fiatprice = 0

if info["hashrate"] > 0:
    if options.diff > 0:
        diff = options.diff
    elif md > 0:
        diff = md
    else:
        diff = info["difficulty"]
    
    blocktime = diff / info["hashrate"]
    
    output = profit(blocktime, info["blockreward"], options.coin, options.watts, options.kwhprice, fiatprice, options.basecur)

    prettyprint(output)


