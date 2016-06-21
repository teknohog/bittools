#!/usr/bin/env python

# by teknohog

# Print a random string of 64 hex digits. This works as a payment ID
# in Cryptonote coins such as Boolberry and Monero.

import random

output = ""

# hex(0).strip("0x") gives ""
for i in range(64):
    output += hex(random.randrange(16))[2]

print(output)
