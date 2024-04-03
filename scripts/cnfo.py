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

import argparse
parser = argparse.ArgumentParser()

def send(wallet, options):
    # 2020-08-11 Transfer using RPC to the wallet server. Written for
    # Zano but should work similarly for other Cryptonote coins.
    # https://docs.zano.org/reference#transfer-2

    # Simple send, no payment ID for now

    address = options.sendto[0]
    amount = float(options.sendto[1])
    txfee = options.txfee
    mixin = options.mixin

    # List of address+amount pairs. Remember to use number of base
    # units for amount and fee, with integer type.
    dest = [{"address": address, "amount": int(amount/baseunit[options.coin])}]
    
    print("About to send %s %f to %s with txfee %f and mixin %i" % (currency[options.coin], amount, address, txfee, mixin))
    
    if confirm():
        result = wallet.transfer(destinations = dest, fee = int(txfee/baseunit[options.coin]), mixin = mixin)
        print(result)
    else:
        print("Confirmation failed, not sending.")


parser.add_argument("-A", "--aeon", action="store_const", const="aeon", dest="coin", default="boolberry", help="Connect to Aeon daemon")

#parser.add_argument("--aliasinfo", default = "", help="BBR alias details")

parser.add_argument("--basecur", default = "EUR", help="Base currency for coin and kWh prices, default EUR")

parser.add_argument("--boolberry", action="store_const", const="boolberry", dest="coin", default="boolberry", help="Connect to Boolberry daemon (default)")

parser.add_argument("-d", "--diff", type=float, default = 0, help="Set difficulty manually for mining estimation")

parser.add_argument("--listaliases", const = "listaliases", action="store_const", help="List all BBR aliases")

parser.add_argument("-M", "--monero", action="store_const", const="monero", dest="coin", default="boolberry", help="Connect to Monero daemon")

parser.add_argument("--mixin", type = int, default = 2, help="Mixin count for transfer, default %(default)s")

parser.add_argument("-N", "--zano", action="store_const", const="zano", dest="coin", default="boolberry", help="Connect to Zano daemon")

parser.add_argument("-r", "--hashrate", dest="hashrate", type=float, default = 0, help="Hashes/sec from external miners")

parser.add_argument("-S", "--stake", dest="stake", type=float, default = 0, help="Stake amount for PoS mining estimation")

parser.add_argument("-s", "--sendto", nargs = 2, help = "Send coins: address followed by amount")

parser.add_argument("-t", "--transactions", dest="transactions", type = int, nargs = "?", const = 10, help="List the number of recent transactions, default 10")

parser.add_argument("--txfee", type = float, default = 0.01, help="Transfer fee, default %(default)s")

parser.add_argument("-u", "--url", dest="url", default="", help="Connect to a different URL, instead of your local daemon")

parser.add_argument("-v", "--verbose", action = "store_true")

parser.add_argument("-W", "--watts", dest="watts", type=float, default = 0, help="Power usage of miners for profitability calculation")

parser.add_argument("-w", "--kwhprice", dest="kwhprice", type=float, default = 0, help="kWh price for profitability calculation")

parser.add_argument("--walletport", type=int, default = 0, help="Connect to wallet server on this port")

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

# 2020-08-11 Wallet ports may vary much more, so specify daemon ports only
rpcport = {
    "aeon": "11181",
    "boolberry": "10102",
    "monero": "18081",
    "zano": "11211",
}

if options.walletport > 0:
    # 2020-08-11 
    url = "http://127.0.0.1:%i/json_rpc" % options.walletport
    wallet = Server(url)
    
    # method not found
    #print(wallet.get_transfers())
    
    # needs payment id
    #print(wallet.get_payments())

    if options.sendto:
        send(wallet, options)
    elif options.transactions:
        # 2024-04-02 Needs nonzero count to show anything meaningful
        res = wallet.get_recent_txs_and_info(exclude_mining_txs = False, count = options.transactions, exclude_unconfirmed = False)

        output = [["Date", "Type", "Amount"]]

        # The order is reversed for the latest transactions. Don't use
        # order = "FROM_BEGIN_TO_END" as it will show the first
        # transactions of the wallet instead.
        for tx in res["transfers"][::-1]:
            if tx["is_income"]:
                if tx["is_mining"]:
                    t = "Mine"
                else:
                    t = "Recv"
            else:
                t = "Send"

            output.append([str(ctime(tx["timestamp"])), t, str(baseunit[options.coin]*tx["amount"])])
            
        prettyprint(output)
            
    else:
        # Address and balance are good defaults to show in any case
        print("Address: %s" % wallet.getaddress()['address'])
        print("Balance: %f" % (wallet.getbalance()['balance'] * baseunit[options.coin]))

        if options.verbose:
            print("Wallet info: %s" % wallet.get_wallet_info())
        
    exit()
    
if len(options.url) > 0:
    url = options.url
else:
    url = "http://127.0.0.1:" + rpcport[options.coin] + "/json_rpc"

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

    pos_diff = float(info["pos_difficulty"])
    
    # https://docs.zano.org/docs/stake/estimating-pos-earning/
    # The math notation is messed up, but the text suggests this
    c = pos_diff / 288e12 # Total amount of coins participating in PoS
    pos_daily_rate = 720 / c # 720 PoS blocks per day
    
    output.append(["PoS interest rate", "%f %%/day" % (pos_daily_rate * 100)])
else:
    diff = info["difficulty"]
    
output.append(["difficulty", str(diff)])

md = meandiff(options.coin, diff)
if md > 0:
    output.append(["meandiff", str(md)])

if options.coin == "zano":
    # 2019-10-11 Approximate emission: BBR coinswap + premine + one
    # coin per block, via https://zano.org/finance.html
    moneysupply = 13.8e6 - 5905009.99 + 3.69e6 + info["height"]
else:
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
elif options.stake > 0 and options.coin == "zano":
    # PoS mining estimation. Can use default 0 for watts and kwhprice.
    blocktime = 86400 / (options.stake * pos_daily_rate)
    output += profit(blocktime, blockreward, options.coin, options.watts, options.kwhprice, 0, options.basecur)
    
if len(output) > 0:
    prettyprint(output)
