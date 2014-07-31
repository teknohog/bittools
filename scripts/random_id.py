#!/usr/bin/env python

# by teknohog

# Print a random string of 64 hex digits. This works as a payment ID
# in Cryptonote coins such as Boolberry and Monero.

import random

output = ""

hexdigits = list("0123456789ABCDEF")
for i in range(64):
    output += random.choice(hexdigits)

# Won't work as hex(0).strip("0x") gives "" for some reason
#for i in range(64):
#    output += hex(random.randrange(16)).strip("0x")

print(output)
