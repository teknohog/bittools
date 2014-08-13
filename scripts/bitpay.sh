#!/bin/bash

# by teknohog for simpler? Bitpay POS payment. This parses the address
# and amount from the QR code and calls coinfo.py, which does its
# thing including verification.

# The latter works best outside screen, when ssh'ed from the N900, so
# copy-pasting the verification code works.

# Example QR string. I hand-parsed this at a bar to pay a beer
# directly with coinfo.py, and it's the reason why this helper script
# exists :-P

#INPUT="bitcoin:1DsUEip8CB8uhbygNFs1pUjKirDyGaFtw5?amount=0.012&r=https%3A%2F%2Fbitpay.com%2Fi%2FYEgitE5VZkeMSqZ1CUDd4x"

# Strings containing "&" are awkward to use as shell parameters. You
# could quote the parameter, or just use something nicer:

echo Paste the Bitpay code here:
read

ADDRESS=$(echo $REPLY | sed -Ee 's/bitcoin:([A-Za-z0-9]+)\?.*/\1/')

AMOUNT=$(echo $REPLY | sed -Ee 's/.*amount=([0-9.]+).*/\1/')

coinfo.py -s $ADDRESS $AMOUNT
