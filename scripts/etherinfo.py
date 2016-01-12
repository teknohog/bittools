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
    print("Sending " + str(amount) + " ether to " + toaddr)

    # Save the balance file after sending. The balance won't be
    # updated immediately, so estimate this -- will be less due to
    # transfer fees and whatnot.
    bal = get_balance(fromaddr) - amount

    daemon.eth_sendTransaction({"from": fromaddr, "to": toaddr, "value": tohexwei(amount)})

    balfile = os.path.expanduser("~/.ethereum/keystore/" + fromaddr + ".balance")
    # Newline makes a manual cat cleaner for the shell
    WriteFile(balfile, str(bal) + "\n")
    
def lastsend(fromaddr, toaddr, fraction, minsend):
    balfile = os.path.expanduser("~/.ethereum/keystore/" + fromaddr + ".balance")
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

parser.add_argument("--account_id", "-a", type = int, help = "Index of local account/address, starting from 0 = coinbase, in the order shown in balances")

parser.add_argument("--fraction", "-f", type = float, default = 0.6, help = "Lastsend fraction, default %(default)f")

parser.add_argument("--lastsend", "-l", help = "Send a fraction (-f) of new income (-a) to this address")

parser.add_argument("--minsend", "-m", type = float, default = 1, help = "Lower limit for lastsend, default %(default)f ETH")

parser.add_argument("-r", "--hashrate", dest="hashrate", type=float, help="Hashes/sec from external miners")

parser.add_argument("--sendto", "-s", nargs = 2, help = "Send toaddress amount in ETH")

parser.add_argument("-u", "--url", dest="url", default="http://localhost:8545", help="Connect to a different URL, instead of your local Ethereum daemon")

parser.add_argument("-W", "--watts", dest="watts", type=float, help="Power usage of miners for profitability calculation")

parser.add_argument("-w", "--kwhprice", dest="kwhprice", type=float, help="kWh price in EUR for profitability calculation")

options = parser.parse_args()

daemon = Server(options.url)

info = {"hashrate": float(int(daemon.eth_hashrate(), 16)),
        "balances": map(get_balance, daemon.eth_accounts()),
        "blocks": int(daemon.eth_blockNumber(), 16),
        "difficulty": float(int(daemon.eth_getBlockByNumber("latest", False)["difficulty"], 16)),
        "peers": int(daemon.net_peerCount(), 16),
        }

info["total balance"] = sum(info["balances"])

if options.account_id > -1:
    aid = options.account_id
    fromaddr = daemon.eth_accounts()[aid]

    if options.sendto:
        toaddr = options.sendto[0]
        amount = int(options.sendto[1])

        send(fromaddr, toaddr, amount)
        exit()

    elif len(options.lastsend) > 0:
        lastsend(fromaddr, options.lastsend, options.fraction, options.minsend)
        exit()

    else:
        # Just add that address into general info
        info["account " + str(aid) + " address"] = fromaddr
        
md = meandiff("ethereum")
if md > 0:
    info["meandiff"] = md

if options.hashrate:
    info["hashrate"] = options.hashrate
    
dictprint(info)

blockreward = 5
output = []

# Don't tax the price server if not calculating full profit
if info["hashrate"] > 0 and options.kwhprice and options.watts:
    if md > 0:
        diff = md
    else:
        diff = info["difficulty"]
    
    time = diff / info["hashrate"]

    tp = timeprint(time)
    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])
    
    coinsperday = blockreward / time * 86400

    output.append(["Average payout", str(coinsperday) + " ETH/day"])

    fiatprice = coin_price("ETH")

    if fiatprice > 0:

        fiatpay = coinsperday * fiatprice

        output.append(["1 ETH", str(fiatprice) + " EUR"])
        output.append(["Fiat payout", str(fiatpay) + " " + "EUR/day"])

        if options.watts > 0 and options.kwhprice > 0:
            cost = options.kwhprice * options.watts / 1000 * 24
        
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

    prettyprint(output)


