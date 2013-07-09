bittools -- command line tools for various cryptocurrency daemons
(Bitcoin/Litecoin/Namecoin/PPCoin/CHNcoin/Primecoin)

by Risto A. Paju / teknohog
BTC: 1HkL2iLLQe3KJuNCgKPc8ViZs83NJyyQDM
LTC: LMuSoipjtRtPwD8VFyKypUTt6nXQHH8zW2


bitcoin-update.sh
=================

Build and update the latest git version of bitcoind on a unix
system. This is aimed at Gentoo Linux, where the system-wide
compilation options are automatically found. For other unices, you may
want to specify some options in the script.

At minimum, the BASEDIR and INSTALLDIR locations near the beginning of
the script should be edited to your taste.

Requires: openssl, boost and db, in addition to usual development
tools.


coinfo.py
=========

A simplified command-line interface to some of the functions of
bitcoind. To communicate with the daemon it uses python-jsonrpc which
can be downloaded here:

http://json-rpc.org/wiki/python-json-rpc

By default, the script connects to your locally running bitcoind,
using credentials found in ~/.bitcoin/bitcoin.conf.

The script is fairly self-documenting with the -h or --help option.


Info examples
-------------

One aim of this script was to provide shorthand commands and output
for some common tasks. For example, instead of writing

$ ./bitcoind listtransactions

which is easy to mess up, as there is often no tab completion for
options, you can write coinfo.py -t. And instead of a messy output of
pure JSON, you get a compact list of dates, accounts and amounts. With
a warning if the transaction is not yet verified.

Another example of such information is the hashrate calculator:

$ coinfo.py -r 1337e6
balance:    xxxx
difficulty: 1379192.28823
testnet:    False

Average time between blocks: 51.2789981443 d
Average payout:              0.975058051238 BTC/d

Next difficulty expected in: 3.47916666667 d


Sending BTC
-----------

coinfo.py -s address amount

It presents a warning if you have recently sent to the same address,
and asks for confirmation in a random way to reduce accidents.


Exporting and importing private keys
------------------------------------

coinfo.py -e prints out the private key of each address, followed by
the account (label) on the same line. After saving to a file (for
example: coinfo.py -e > keyfile) these can be imported to another
wallet using coinfo.py -i keyfile.

This is an advanced feature which may break things, so remember to
back up your wallets first.

However, nothing is destroyed on the export side. You can access the
same addresses on both wallets after a succesful import.

Also note that bitcoind takes several minutes to import one
address. It probably depends on many factors such as the number of
transactions.

I chose to export all addresses, because I mainly use this for merging
wallets (deleting the source wallet afterwards). However, the import
side is easy to control by editing the keyfile.

Why merge wallets instead of simply sending coins?

* Avoid transaction fees
* Keep the receiving addresses alive
