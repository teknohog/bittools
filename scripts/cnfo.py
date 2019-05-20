#!/usr/bin/env python

# by teknohog 2015-05-31

# This is a work in progress for coinfo.py equivalent functions for
# Cryptonote coins -- BBR and Monero for now, but can be easily extended.

# For now, this only accesses the daemon for simple data such as
# difficulty and block reward. The wallets could also be accessed
# using https://wiki.bytecoin.org/wiki/Wallet_JSON_RPC_API but the
# separate wallets complicate things a bit, so I now use simple shell
# wrappers to send money.

from bittools import *

def wallet_server(coin):
    # Not needed for all functions, so keep this separate
    
    # ./simplewallet --wallet-file wallet.bin --rpc-bind-port=10103 --password xxxx
    url = "http://127.0.0.1:" + rpcport["wallet"][coin] + "/json_rpc"
    return Server(url)

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("-A", "--aeon", action="store_const", const="aeon", dest="coin", default="boolberry", help="Connect to Aeon daemon")

#parser.add_argument("--aliasinfo", default = "", help="BBR alias details")

parser.add_argument("--basecur", default = "EUR", help="Base currency for coin and kWh prices, default EUR")

parser.add_argument("--boolberry", action="store_const", const="boolberry", dest="coin", default="boolberry", help="Connect to Boolberry daemon (default)")

parser.add_argument("-d", "--diff", type=float, default = 0, help="Set difficulty manually for mining estimation")

parser.add_argument("--listaliases", const = "listaliases", action="store_const", help="List all BBR aliases")

parser.add_argument("-M", "--monero", action="store_const", const="monero", dest="coin", default="boolberry", help="Connect to Monero daemon")

parser.add_argument("-N", "--zano", action="store_const", const="zano", dest="coin", default="boolberry", help="Connect to Zano daemon")

parser.add_argument("-r", "--hashrate", dest="hashrate", type=float, default = 0, help="Hashes/sec from external miners")

parser.add_argument("-t", "--transactions", dest="transactions", action="store_true", default=False, help="List recent transactions")

parser.add_argument("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local daemon")

parser.add_argument("-v", "--verbose", action = "store_true")

parser.add_argument("-W", "--watts", dest="watts", type=float, help="Power usage of miners for profitability calculation")

parser.add_argument("-w", "--kwhprice", dest="kwhprice", type=float, help="kWh price for profitability calculation")

options = parser.parse_args()

# Atomic unit of currency
baseunit = {
    "aeon": 1e-12,
    "boolberry": 1e-12,
    "monero": 1e-12,
    "zano": 1e-12, # ?
}

reward_divisor = {
    "aeon": 2**18,
    "boolberry": 2**20,
    "monero": 2**20,
    "zano": 2**20, # ?
}

rpcport = {
    "daemon":
    {
        "aeon": "11181",
        "boolberry": "10102",
        "monero": "18081",
        "zano": "11211",
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
    exit()
    
if len(options.url) > 0:
    url = options.url
else:
    url = "http://127.0.0.1:" + rpcport["daemon"][options.coin] + "/json_rpc"

# https://wiki.bytecoin.org/wiki/Daemon_JSON_RPC_API
daemon = Server(url)

if options.listaliases:
    aad = daemon.get_all_alias_details()

    if aad["status"] == "OK":
        output = []
        for line in aad["aliases"]:
            output.append([line["alias"], line["address"]])
        prettyprint(output)

    exit()

# not working
#elif options.aliasinfo:
#    print(daemon.get_alias_details({"alias": options.aliasinfo}))
#    exit()
    
output = []

lasthead = daemon.getlastblockheader()["block_header"]

# More up-to-date info. This does not contain block reward, so keep
# lasthead for that for now.
if options.coin in ["boolberry", "zano"]:
    info = daemon.getinfo()
else:
    info = daemon.get_info()

output.append(["height", str(info["height"])])

if options.coin == "zano":
    # PoW reward for mining calculations. Lasthead may contain much higher PoS
    blockreward = 1
else:
    blockreward = lasthead["reward"] * baseunit[options.coin]

output.append(["blockreward", str(blockreward)])

if options.diff > 0:
    diff = options.diff
elif options.coin == "zano":
    diff = info["pow_difficulty"]
else:
    diff = info["difficulty"]
    
output.append(["difficulty", str(diff)])

md = meandiff(options.coin, diff)
if md > 0:
    output.append(["meandiff", str(md)])

# This is the basic Cryptonote scheme, so it won't work if there's
# tail emission or something. Also, it's only an estimate.
moneysupply = (2**64 - 1) * baseunit[options.coin] - blockreward * reward_divisor[options.coin]
output.append(["moneysupply", str(moneysupply)])

if options.verbose:
    fiatprice = coin_price(options.coin, options.basecur)

    if fiatprice > 0:
        output.append([options.basecur + " price", str(fiatprice)])

if options.hashrate > 0:
    if md > 0 and not options.diff:
        diff = md
    
    blocktime = diff / options.hashrate
    output += profit(blocktime, blockreward, options.coin, options.watts, options.kwhprice, 0, options.basecur)

if len(output) > 0:
    prettyprint(output)
