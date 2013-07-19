#!/bin/bash

# by teknohog

# Estimate primecoin performance from the primemeter log entries by
# taking averages of last few entries. The 5-chain rate only works
# with some primecoin builds, for example the hp tree by mikaelh2.

LINES=20

LOGFILE=~/.primecoin/debug.log

TAIL=`mktemp`

grep primemeter $LOGFILE | tail -n $LINES > $TAIL

PRIMERATES="`sed -e 's|.* \([0-9]\+\) prime/h.*|\1|g' < $TAIL`"
TESTRATES="`sed -e 's|.* \([0-9]\+\) test/h.*|\1|g' < $TAIL`"
FCRATES="`sed -e 's|.* \([0-9]\+\) 5-chains/h.*|\1|g' < $TAIL`"

rm $TAIL

function average () {
    SUM=0
    
    for R in $RATES; do
	SUM=$((SUM + R))
    done

    RATE=`echo "$SUM / $LINES" | bc -l`
    RATE=${RATE//.*/}

    echo $RATE
}

function min () {
    RESULT=999999999999999999

    for R in $RATES; do
	if [ $R -lt $RESULT ]; then
	    RESULT=$R
	fi
    done

    echo $RESULT
}

function max () {
    RESULT=0

    for R in $RATES; do
	if [ $R -gt $RESULT ]; then
	    RESULT=$R
	fi
    done

    echo $RESULT
}

RATES="$PRIMERATES"
echo `average` primes/h, `min` to `max`

RATES="$TESTRATES"
echo `average` tests/h, `min` to `max`

RATES="$FCRATES"
echo `average` 5-chains/h, `min` to `max`


