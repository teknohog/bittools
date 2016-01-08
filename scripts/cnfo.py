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

import os.path
import re
import sys

from time import time

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

def coin_price(coin):
    # Assume EUR as the base price for now
    cn_url = "https://www.cryptonator.com/api/ticker/" + currency[coin] + "-EUR"

    # http://stackoverflow.com/questions/12965203/how-to-get-json-from-webpage-into-python-script
    import urllib, json

    try:
        response = urllib.urlopen(cn_url);
        data = json.loads(response.read())

        return float(data["ticker"]["price"])
    except:
        return 0

def ReadLines(f):
    File = open(f, "r")
    contents = File.readlines()
    File.close()
    return contents

def linear_regression(pairs):
    # Data usually comes in x, y pairs, so choose it as my input format
    
    # There should be something clever with zip() etc. but I can't
    # get it working now :-/
    xy = [[], []]
    for p in pairs:
        for i in [0, 1]:
            xy[i].append(float(p[i]))

    n = len(xy[0])
    sx = sum(xy[0])
    sy = sum(xy[1])
    sx2 = sum(map(lambda z: z**2, xy[0]))
    sy2 = sum(map(lambda z: z**2, xy[1]))
    sxy = sum(map(lambda a, b: a*b, xy[0], xy[1]))

    # In case of constant y, this makes div by zero error, and should be zero
    if n*sx2 != sx**2:
        b = (n*sxy - sx*sy) / (n*sx2 - sx**2)
    else:
        b = 0

    a = (sy - b*sx) / n

    #r = (n*sxy - sx*sy) / ((n*sx2 - sx**2)*(n*sy2 - sy**2))**0.5

    return (a, b)
    
def meandiff(coin):
    # Use meandiff.sh history if available
    if coin == "boolberry":
        dirname = "boolb"
    else:
        dirname = coin
        
    difflog = os.path.expanduser("~/." + dirname + "/difflog")
    
    if os.path.exists(difflog):
        l = ReadLines(difflog)

        # Meandiff was originally about smoothing random
        # variations. However, if the diff is obviously
        # increasing/decreasing, use that for prediction. If not, this
        # performs the smoothing anyway.

        if len(l) < 2:
            return 0
        
        # difflog now contains time, diff pairs
        pairs = map(lambda a: a.split(), l)
                
        ab = linear_regression(pairs)

        # Estimate a current diff
        return ab[0] + ab[1] * time()
    else:
        return 0

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

meandiff = meandiff(options.coin)
if meandiff > 0:
    output.append(["meandiff", str(meandiff)])

if options.hashrate > 0:
    if meandiff > 0:
        diff = meandiff
    
    time = diff / options.hashrate

    tp = timeprint(time)
    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])
    
    coinsperday = blockreward / time * 86400

    output.append(["Average payout", str(coinsperday) + " " + currency[options.coin] + "/day"])

    fiatprice = coin_price(options.coin)    

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
