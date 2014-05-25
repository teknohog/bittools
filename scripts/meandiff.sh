#!/bin/bash

# by teknohog

# Collect recent difficulty statistics for the given coin using the -s
# option. By default, show the average of last $LINES entries.

LINES=10

function average () {
    TOTAL=0
    # Note the actual number of entries, which may be less than $LINES
    N=0

    for LINE in `tail -n $LINES $LOGFILE`; do
	TOTAL=`echo $TOTAL + $LINE | bc -l`
	N=$((++N))
    done

    echo $TOTAL / $N | bc -l
}

POS=false
SET=false
PROJECT=bitcoin
while getopts aBcDEGgHIjKLlmnPpSsx opt; do
    case "$opt" in
	a) PROJECT=AuroraCoin ;;
	B) PROJECT=blakecoin ;;
	c) PROJECT=chncoin ;;
	D) PROJECT=dogecoin ;;
	E) PROJECT=electron ;;
	G) PROJECT=GroestlCoin ;;
	g)
	    PROJECT=shibecoin
	    POS=true
	    ;;
        H) PROJECT=photon ;;
	I) PROJECT=riecoin ;;
	j) PROJECT=primio ;;
	K) PROJECT=darkcoin ;;
	L) PROJECT=Slothcoin ;;
	l) PROJECT=litecoin ;;
	m) PROJECT=maxcoin ;;
	n) PROJECT=namecoin ;;
	P) PROJECT=primecoin ;;
	p)
	    PROJECT=ppcoin
	    POS=true
	    ;;
	S) PROJECT=skeincoin ;;
	s) SET=true ;;
	x) PROJECT=dirac ;;
    esac
done

case $PROJECT in
    Slothcoin)
	LOGFILE=~/.SlothCoin/difflog
	;;
    shibecoin)
	LOGFILE=~/.ShibeCoin/difflog
	;;
    *)
	LOGFILE=~/.$PROJECT/difflog
	;;
esac

CMD=~/distr.projects/$PROJECT-git/${PROJECT}d

if $SET; then
    # top up the logfile
    if $POS; then
	# Get the PoW entry from a mixed PoS/PoW coin
	$CMD getdifficulty | grep work | \
	    sed -Ee 's/.* ([0-9]+\.[0-9]+),.*/\1/' >> $LOGFILE
    else
	$CMD getdifficulty >> $LOGFILE
    fi

    # and prune it
    tail -n $LINES $LOGFILE > $LOGFILE.tmp && mv $LOGFILE.tmp $LOGFILE
else
    average
fi

