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

SET=false
PROJECT=bitcoin
while getopts aBcDEILlmnPpSs opt; do
    case "$opt" in
	a) PROJECT=AuroraCoin ;;
	B) PROJECT=blakecoin ;;
	c) PROJECT=chncoin ;;
	D) PROJECT=dogecoin ;;
	E) PROJECT=ecoin ;;
	I) PROJECT=riecoin ;;
	L) PROJECT=Slothcoin ;;
	l) PROJECT=litecoin ;;
	m) PROJECT=maxcoin ;;
	n) PROJECT=namecoin ;;
	P) PROJECT=primecoin ;;
	p) PROJECT=ppcoin ;;
	S) PROJECT=skeincoin ;;
	s) SET=true ;;
    esac
done

if [ "$PROJECT" == "Slothcoin" ]; then
    LOGFILE=~/.SlothCoin/difflog
else
    LOGFILE=~/.$PROJECT/difflog
fi

CMD=~/distr.projects/$PROJECT-git/${PROJECT}d

if $SET; then
    # top up the logfile
    $CMD getdifficulty >> $LOGFILE

    # and prune it
    tail -n $LINES $LOGFILE > $LOGFILE.tmp && mv $LOGFILE.tmp $LOGFILE
else
    average
fi

