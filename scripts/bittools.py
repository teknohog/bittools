# 2016-01-12 by teknohog

# Common functions for bittools Python scripts

import os.path
from math import ceil, exp
from time import ctime, time

# https://github.com/joshmarshall/jsonrpclib
from jsonrpclib import Server

from sys import exit, version_info

def ReadLines(f):
    File = open(f, "r")
    contents = File.readlines()
    File.close()
    return contents

def printlength(s):
    # get rid of newlines for the printable length calculation
    return len(s.strip())

def prettyprint(array, delimiter=" "):
    # I guess this verges on something that should use curses instead

    if len(array) > 0:
        columns = len(array[0])

        width = []
        for column in range(columns):
            width.append(max(map(lambda x: printlength(x[column]), array)))

        for i in array:
            print(delimiter.join(map(lambda col: i[col] + " "*(width[col] - printlength(i[col])), range(columns - 1))) + delimiter + i[columns-1])

def timeprint(time):
    # This is used more generally, so provide the number as a number,
    # and the unit separately

    # Order is important, so no dictionaries
    units = ["days", "h", "min"]
    limits = [86400., 3600., 60.] # floats for automatic conversion
    for i in range(len(limits)):
        if time >= limits[i]:
            return [time / limits[i], units[i]]

    return [time, "s"]

def coin_price(coin, basecur):
    import json

    if version_info >= (3, 0):
        from urllib.request import urlopen
    else:
        from urllib2 import urlopen
        
    # 2018-02-18 Coinmarketcap uses full names instead of tickers, and
    # it is easier to map coin->ticker here
    cur = currency[coin]
    
    if cur == basecur:
        return 1
    
    api_urls = [
        "https://api.coingecko.com/api/v3/simple/price?ids=" + cur + "&vs_currencies=" + basecur,
        "https://api.coinmarketcap.com/v1/ticker/" + coin + "/", 
        "https://www.cryptocompare.com/api/data/price?fsym=" + cur + "&tsyms=" + basecur,
        "https://api.cryptonator.com/api/ticker/" + cur + "-" + basecur,
    ]
    
    for url in api_urls:
        try:
            response = urlopen(url, timeout = 5)
            data = json.loads(response.read())
            
            if "coingecko" in url and len(data[cur.lower()]) > 0:
                return float(data[cur.lower()][basecur.lower()])
                
            elif "coinmarketcap" in url:
                if basecur in ["BTC", "USD"]:
                    return float(data[0]["price_" + basecur.lower()])
                elif "BTC" not in [cur, basecur]:
                    return coin_price_via_btc(coin, basecur)
            
            elif "cryptonator" in url:
                return float(data["ticker"]["price"])

            elif "cryptocompare" in url and cur != "BBR":
                # outdated for BBR
                
                if len(data["Data"]) == 0 and "BTC" not in [cur, basecur]:
                    return coin_price_via_btc(coin, basecur)
                else:
                    return float(data["Data"][0]["Price"])
        except:
            pass

    return 0

def coin_price_via_btc(coin, basecur):
    # Common issue for price APIs, so factor out
    p1 = coin_price(coin, "BTC")
    p2 = coin_price("bitcoin", basecur)
    return p1*p2

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

    # Repeating data points may induce div by zero
    if n*sx2 != sx**2:
        b = (n*sxy - sx*sy) / (n*sx2 - sx**2)
    else:
        b = 0

    a = (sy - b*sx) / n

    #r = (n*sxy - sx*sy) / ((n*sx2 - sx**2)*(n*sy2 - sy**2))**0.5

    return (a, b)

def meandiff(coin, diffnow = 0):
    # Use meandiff.sh history if available
    if coin == "boolberry":
        dirname = "boolb"
    elif coin == "monero":
        dirname = "bitmonero"
    elif coin == "zano":
        dirname = "Zano"
    else:
        dirname = coin
        
    difflog = os.path.expanduser("~/." + dirname + "/difflog")

    # Don't use if more than a few hours old
    if os.path.exists(difflog) and time() - os.path.getmtime(difflog) < 1e4:
        # unique lines
        l = set(ReadLines(difflog))

        # Meandiff was originally about smoothing random
        # variations. However, if the diff is obviously
        # increasing/decreasing, use that for prediction. If not, this
        # performs the smoothing anyway.

        if len(l) < 2:
            return 0
        
        # difflog now contains time, diff pairs
        pairs = list(map(lambda a: a.split(), l))

        # Current difficulty is a valid, useful data point
        if diffnow > 0:
            pairs.append([time(), diffnow])

        ab = linear_regression(pairs)

        # Estimate a current diff
        return ab[0] + ab[1] * time()
    else:
        return 0

def profit(blocktime, reward, coin, watts, kwhprice, fiatprice = 0, basecur = "EUR"):
    # The conventions are slightly different between coin families, so
    # try to make this general enough while factoring out everything
    # in common
    
    output = []

    cur = currency[coin]
    
    tp = timeprint(blocktime)
    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])
    
    coinsperday = reward / blocktime * 86400

    output.append(["Average payout", str(coinsperday) + " " + cur + "/day"])

    # We may already have this from balance display, so don't bother
    # the server. It may still be unavailable, though.
    if fiatprice <= 0:
        fiatprice = coin_price(coin, basecur)

    if fiatprice > 0:
        fiatpay = coinsperday * fiatprice

        output.append(["1 " + cur, str(fiatprice) + " " + basecur])
        output.append(["Fiat payout", str(fiatpay) + " " + basecur + "/day"])

        if watts > 0 and kwhprice > 0:
            cost = kwhprice * watts / 1000 * 24
            pratio = fiatpay / cost
                
            if pratio > 2:
                emo = ":D"
            elif pratio > 1:
                emo = ":)"
            else:
                emo = ":("

            output.append(["Payout/cost", str(pratio) + " " + emo])
            output.append(["Net profit", str(fiatpay - cost) + " " + basecur + "/day"])

    return output

def exp_decay(init, blocks, period, base=0.5):
    p = ceil(float(blocks) / float(period - 2))
    return init * base**(p - 1)

if version_info >= (3, 0):
    # input() is available in python2, but it's more like eval()
    # python3's input() and python2's raw_input() just return the string
    def raw_input(s):
        return input(s)
    
# These need to be available for coin_price so moved here
currency = {
    "AuroraCoin": "AUR",
    "bitcoin": "BTC",
    "btcprivate": "BTCP",
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
    "peercoin": "PPC",
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
    "zano": "ZANO", # ?
    "zcash": "ZEC",
    "zclassic": "ZCL",
    "zcoin": "XZC",
    "zen": "ZEN",

    "aeon": "AEON",
    "boolberry": "BBR",
    "monero": "XMR",

    "ethereum": "ETH",
    "ethereum-classic": "ETC",
}
