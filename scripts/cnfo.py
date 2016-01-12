#!/usr/bin/env python

# by teknohog 2015-05-31

# This is a work in progress for coinfo.py equivalent functions for
# Cryptonote coins -- BBR and Monero for now, but can be easily extended.

# For now, this only accesses the daemon for simple data such as
# difficulty and block reward. The wallets could also be accessed
# using https://wiki.bytecoin.org/wiki/Wallet_JSON_RPC_API but the
# separate wallets complicate things a bit, so I now use simple shell
# wrappers to send money.

# https://github.com/joshmarshall/jsonrpclib
# Package in Gentoo Portage, seems to work better for Cryptonotes than
# the old jsonrpc
from jsonrpclib import Server

import sys

from bittools import *

def wallet_server(coin):
    # Not needed for all functions, so keep this separate
    
    # ./simplewallet --wallet-file wallet.bin --rpc-bind-port=10103 --password xxxx
    url = "http://127.0.0.1:" + rpcport["wallet"][coin] + "/json_rpc"
    return Server(url)

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("--boolberry", action="store_const", const="boolberry", dest="coin", default="boolberry", help="Connect to Boolberry daemon (default)")

parser.add_argument("-M", "--bitmonero", action="store_const", const="monero", dest="coin", default="boolberry", help="Connect to Monero daemon")

parser.add_argument("-r", "--hashrate", dest="hashrate", type=float, help="Hashes/sec from external miners")

parser.add_argument("-t", "--transactions", dest="transactions", action="store_true", default=False, help="List recent transactions")

parser.add_argument("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local daemon")

parser.add_argument("-W", "--watts", dest="watts", type=float, help="Power usage of miners for profitability calculation")

parser.add_argument("-w", "--kwhprice", dest="kwhprice", type=float, help="kWh price in EUR for profitability calculation")

options = parser.parse_args()

currency = {
    "boolberry": "BBR",
    "monero": "XMR",
}

# Atomic unit of currency
baseunit = {
    "boolberry": 1e-12,
    "monero": 1e-12,
}

rpcport = {
    "daemon":
    {
        "boolberry": "10102",
        "monero": "18081",
    },
    "wallet":
    {
        "boolberry": "10103",
    },
}


if options.transactions:
    wallet = wallet_server(options.coin)
    
    # method not found
    print(wallet.get_transfers())
    
    # needs payment id
    #print(wallet.get_payments())

    # works, keep for later
    #print(wallet.getbalance()['unlocked_balance'] * baseunit[options.coin])
    sys.exit()
    
if len(options.url) > 0:
    url = options.url
else:
    url = "http://127.0.0.1:" + rpcport["daemon"][options.coin] + "/json_rpc"

# https://wiki.bytecoin.org/wiki/Daemon_JSON_RPC_API
daemon = Server(url)

output = []

lasthead = daemon.getlastblockheader()["block_header"]

blocks = lasthead["height"]
output.append(["blocks", str(blocks)])

blockreward = lasthead["reward"] * baseunit[options.coin]
output.append(["blockreward", str(blockreward)])

diff = lasthead["difficulty"]
output.append(["difficulty", str(diff)])

md = meandiff(options.coin)
if md > 0:
    output.append(["meandiff", str(md)])

if options.hashrate > 0:
    if md > 0:
        diff = md
    
    time = diff / options.hashrate

    tp = timeprint(time)
    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])
    
    coinsperday = blockreward / time * 86400

    output.append(["Average payout", str(coinsperday) + " " + currency[options.coin] + "/day"])

    fiatprice = coin_price(currency[options.coin])

    if fiatprice > 0:

        fiatpay = coinsperday * fiatprice

        output.append(["1 " + currency[options.coin], str(fiatprice) + " EUR"])
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

if len(output) > 0:
    prettyprint(output)
