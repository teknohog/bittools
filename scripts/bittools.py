# 2016-01-12 by teknohog

# Common functions for bittools Python scripts

import os.path
from time import time

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

def coin_price(cur):
    # Assume EUR as the base price for now
    cn_url = "https://www.cryptonator.com/api/ticker/" + cur + "-EUR"

    # http://stackoverflow.com/questions/12965203/how-to-get-json-from-webpage-into-python-script
    import urllib, json

    try:
        response = urllib.urlopen(cn_url);
        data = json.loads(response.read())

        return float(data["ticker"]["price"])
    except:
        return 0

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

def meandiff(coin):
    # Use meandiff.sh history if available
    if coin == "boolberry":
        dirname = "boolb"
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
        pairs = map(lambda a: a.split(), l)
                
        ab = linear_regression(pairs)

        # Estimate a current diff
        return ab[0] + ab[1] * time()
    else:
        return 0

def profit(blocktime, reward, cur, watts, kwhprice):
    # The conventions are slightly different between coin families, so
    # try to make this general enough while factoring out everything
    # in common
    
    output = []
    
    tp = timeprint(blocktime)
    output.append(["\nAverage time between blocks", str(tp[0]) + " " + tp[1]])
    
    coinsperday = reward / blocktime * 86400

    output.append(["Average payout", str(coinsperday) + " " + cur + "/day"])

    fiatprice = coin_price(cur)

    if fiatprice > 0:
        fiatpay = coinsperday * fiatprice

        output.append(["1 " + cur, str(fiatprice) + " EUR"])
        output.append(["Fiat payout", str(fiatpay) + " " + "EUR/day"])

        if watts > 0 and kwhprice > 0:
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

    return output
