bittools -- unix command line tools for various cryptocurrency daemons
(AuroraCoin, Bitcoin, BlakeBitcoin, Blakecoin, Boolberry, CHNcoin,
Cryptonite, Dash, Dirac, Dogecoin, eCoin, Electron, Ethereum,
ExclusiveCoin, Gapcoin, GroestlCoin, Litecoin, Lithium, Maxcoin,
Monero, Namecoin, Photon, PPCoin, Primecoin, Primio, Riecoin,
ShibeCoin, Skeincoin, Slothcoin, Universalmolecule, Tjcoin,
Vanillacoin, Vertcoin, Virtacoin, Zcash)

by Risto A. Paju / teknohog
BTC: 1HkL2iLLQe3KJuNCgKPc8ViZs83NJyyQDM
LTC: LMuSoipjtRtPwD8VFyKypUTt6nXQHH8zW2


bitcoin-update.sh
=================

Build and update the latest git version of *coind on a unix
system. This is aimed at Gentoo Linux, where the system-wide
compilation options are automatically found. For other unices, you may
want to specify some options in the script.

At minimum, the BASEDIR and INSTALLDIR locations near the beginning of
the script should be edited to your taste.

Requires: openssl, boost and db, in addition to usual development
tools.


primemeter.sh
=============

Logfile parser for primecoin, to show sensible averages of performance
metrics.


coinfo.py
=========

A simplified command-line interface to some of the functions of
*coind. To communicate with the daemon it uses jsonrpclib from 

https://github.com/joshmarshall/jsonrpclib

which is also available in Linux distributions.

By default, the script connects to your locally running *coind,
using credentials found in ~/.bitcoin/bitcoin.conf.

The script is fairly self-documenting with the -h or --help option.


cnfo.py
=======

A work in progress to replicate coinfo.py for Cryptonote coins. Note
that wallets are not accessible from the main daemon, so this only
provides info for applications such as profit estimation.

(The simplewallet also provides its own RPC interface, but its command
line also suffices for common tasks.)


etherinfo.py
============

For Ethereum. Handles wallets/accounts too, with the difference to
coinfo.py that the 'from' address for sends must be specified, and
here a simple index is used.


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


Profitability estimation
------------------------

With a known hashrate, coinfo.py now uses price data from
https://www.cryptonator.com/ to convert daily returns into fiat
currency. For example, mining Darkcoins with 8 Mhash/s:

$ coinfo.py -Kr 8e6
balance    *****
testnet    False
difficulty 3018.54586397

Average time between blocks 18.7565910984 days
Average payout              0.303997974714 DRK/day
Fiat payout                 1.51651756614 EUR/day

To find out if this is worth it, you can also enter the total wattage
and the EUR price of a kWh:

$ coinfo.py -Kr 8e6 -W 270 -w 0.1274
balance    *****
testnet    False
difficulty 3018.54586397

Average time between blocks 18.7565910984 days
Average payout              0.303997974714 DRK/day
Fiat payout                 1.51591177114 EUR/day
Payout/cost                 1.83624020187 :)
Net profit                  0.690359771137 EUR/day

To use USD (or BTC, or any similar standard) instead of EUR, use
--basecur USD.

Note:

* Cryptonator is a free service provided by a third party, so please
do not overuse this.

* As prices and difficulties vary over time, this can only
give a rough estimate of real profitability. Also, this won't take
merge mining into account. I generally use a spreadsheet to keep track
of these things, with suitable averages (hint: meandiff.sh).


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

Also note that *coind takes several minutes to import one
address. It probably depends on many factors such as the number of
transactions.

I chose to export all addresses, because I mainly use this for merging
wallets (deleting the source wallet afterwards). However, the import
side is easy to control by editing the keyfile.

Why merge wallets instead of simply sending coins?

* Avoid transaction fees
* Keep the receiving addresses alive


Wallet encryption
-----------------

Two explicit options for encryption are available in coinfo.py:

--encrypt for initial encryption of the wallet
--unlock for unlocking the wallet for 1 minute

In addition, the send function will attempt unlocking if initial send
fails. In that case, the wallet is locked immediately afterwards.

The unlock option is particularly important for exporting keys, as
there is no simple method of detecting encryption status. Wallet
backups are not affected, as they will remain encrypted in any case.

Notably, all encryption options will prompt for the passphrase; it is
never used on the command line, where it could end up in the shell
history file.


meandiff.sh
===========

For some coins, the difficulty jumps around considerably during a
single day, making it hard to estimate long-term returns. This script
is used to maintain a sliding average. In addition, the linear
regression provides a short-term trend (use -v).

To first collect the difficulty history, have something like this in
crontab:

13 * * * * meandiff.sh -Bs

Later, meandiff.sh -B will show the average. Coin identifiers are the
same as in other scripts, so this example is for Blakecoin.

The RPC scripts cnfo.py, coinfo.py, etherinfo.py will use the meandiff
log for calculations if available.

Of course, the difficulties of past blocks could be dug from the
blockchain; see meandiff2() in coinfo.py for an
implementation. However, this is notably slower in practice.


random_id.py
============

A simple script to generate a random Payment ID for Cryptonote coins,
such as Boolberry and Monero. Example:

$ ./random_id.py
9923EA057C8AADCE0B5FEB187F329FB50A4B95967F3BD4498332AAACDABE8FE0


bitpay.sh
=========

A wrapper for parsing URLs / QR codes such as

bitcoin:1nvalid4ddressifyoukn0wwh471m34n?amount=3.14&label=foo

for payment. The need for this arose at a Bitpay point-of-sale, but
the URL scheme is not limited to Bitpay. In addition, most other coins
such as litecoin should work.

There are no options, the script prompts for the code, which is
generally copy-pasted from a QR reader or some other application.

This now uses the native binary instead of my Python RPC approach,
with a simple yes/no confirmation dialog.
