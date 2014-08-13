#!/bin/bash

# by teknohog for simpler POS payment using URL / QR code from systems
# like Bitpay. This parses the address and amount from the QR code and
# calls coinfo.py, which does its thing including verification.

# The latter works best outside screen, when ssh'ed from the N900, so
# copy-pasting the verification code works.

# Example QR string. I hand-parsed this at a bar to pay a beer
# directly with coinfo.py, and it's the reason why this helper script
# now exists :-P

#INPUT="bitcoin:1DsUEip8CB8uhbygNFs1pUjKirDyGaFtw5?amount=0.012&r=https%3A%2F%2Fbitpay.com%2Fi%2FYEgitE5VZkeMSqZ1CUDd4x"

# Strings containing "&" are awkward to use as shell parameters. You
# could quote the parameter, or just use something nicer:

echo Paste the Bitpay code here:
read

COIN=$(echo $REPLY | sed -Ee 's/^([a-z]+):.*/\1/')

ADDRESS=$(echo $REPLY | sed -Ee 's/^([a-z]+):([A-Za-z0-9]+).*/\2/')

# Amount may be missing in the simplest versions
if [ -n "$(echo $REPLY | grep amount=)" ]; then
    AMOUNT=$(echo $REPLY | sed -Ee 's/.*amount=([0-9.]+).*/\1/')
else
    echo Please enter/paste the $COIN amount:
    read
    AMOUNT=$REPLY
fi

coinfo.py --$COIN -s $ADDRESS $AMOUNT
