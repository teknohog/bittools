#!/bin/bash

# by teknohog

# Collect recent difficulty statistics for the given coin using the -s
# option. By default, show the average of last $LINES entries.

LINES=10

function lin_reg () {
    if $VERBOSE; then
	cat $LOGFILE
	echo
    fi
    
    # Linear regression to estimate a current diff
    tail -n $LINES $LOGFILE | \
	awk '{n = n + 1
sx = sx + $1
sy = sy + $2
sxy = sxy + $1*$2
sx2 = sx2 + $1**2
sy2 = sy2 + $2**2}
END{b = (n*sxy - sx*sy) / (n*sx2 - sx**2)
a = (sy - b*sx) / n
estimate = a + b*systime()
print "pct_hourly " b/estimate * 3600 * 100
print "estimate " estimate}'
}

function find_cmd () {
    # No need to search this every time, only when we actually need the cmd
    
    # from bitcoin-backup.sh
    # *-cli binary is preferred to *d. For example, in Bitcoin 0.10.0 the
    # daemon no longer works as an RPC client.
    
    for DIR in ${HOME}/distr.projects/${PROJECT}-git /usr/bin; do
	for BIN in ${PROJECT}-cli ${PROJECT}d; do
	    if [ -x "$DIR/$BIN" ]; then
		CMD=$DIR/$BIN
		break
	    fi
	done
	# Break out from the outer loop
	if [ -x "$CMD" ]; then
	    break
	fi
    done
    
    if [ ! -x "$CMD" ]; then
	exit 0
    fi

    echo $CMD
}

POS=false
SET=false
PROJECT=bitcoin
VERBOSE=false
while getopts aBcDEFGgHIjKLlMmnOoPpSsTUVvwXxYyz opt; do
    case "$opt" in
	a) PROJECT=AuroraCoin ;;
	B) PROJECT=blakecoin ;;
	c) PROJECT=chncoin ;;
	D) PROJECT=dogecoin ;;
	E) PROJECT=electron ;;
	F) PROJECT=gapcoin ;;
	G) PROJECT=groestlcoin ;;
	g)
	    PROJECT=shibecoin
	    POS=true
	    ;;
        H) PROJECT=photon ;;
	I) PROJECT=riecoin ;;
	j) PROJECT=primio ;;
	K) PROJECT=dash ;;
	L) PROJECT=Slothcoin ;;
	l) PROJECT=litecoin ;;
	M) PROJECT=bitmonero ;;
	m) PROJECT=maxcoin ;;
	n) PROJECT=namecoin ;;
	O|o)
	    # The -O distinction for boolberry-opencl only matters for
	    # building binaries
	    PROJECT=boolberry
	    ;;
	P) PROJECT=primecoin ;;
	p)
	    PROJECT=ppcoin
	    POS=true
	    ;;
	S) PROJECT=skeincoin ;;
	s) SET=true ;;
	T) PROJECT=Tjcoin ;;
        U) PROJECT=universalmolecule ;;
	V) PROJECT=virtacoin ;;
	v) VERBOSE=true ;;
	w) PROJECT=ethereum ;;
	X) PROJECT=cryptonite ;;
	x) PROJECT=dirac ;;
	Y) PROJECT=lithium ;;
	y) PROJECT=vertcoin ;;
	z)
	    PROJECT=ExclusiveCoin
	    POS=true
	    ;;
    esac
done

case $PROJECT in
    boolberry)
	LOGFILE=~/.boolb/difflog
	;;
    Slothcoin)
	LOGFILE=~/.SlothCoin/difflog
	;;
    shibecoin)
	LOGFILE=~/.ShibeCoin/difflog
	;;
    Tjcoin)
	LOGFILE=~/.TjcoinV2/difflog
	;;
    *)
	LOGFILE=~/.$PROJECT/difflog
	;;
esac

if $SET; then
    # top up the logfile
    case $PROJECT in
	bitmonero|boolberry)
	    DIFF=$(cnfo.py --$PROJECT | grep -m1 difficulty | awk '{print $2}')
	    ;;
	ethereum)
	    DIFF=$(etherinfo.py | grep -m1 difficulty | awk '{print $2}')
	    ;;
	*)
	    # Note: we could just use coinfo.py similarly here, but
	    # the old binary way is faster, which makes a difference
	    # when used dozens of times a day per coin.
	    
	    CMD=$(find_cmd)
	    
	    if $POS; then
		# Get the PoW entry from a mixed PoS/PoW coin
		DIFF=$($CMD getdifficulty | grep work | \
			      sed -Ee 's/.* ([0-9]+\.[0-9]+),.*/\1/')
	    else
		DIFF=$($CMD getdifficulty)
	    fi
	    ;;
    esac

    # don't ruin the difflog if we have problems
    if [ -n "$DIFF" ]; then
	TIME=$(date +%s)
	echo $TIME $DIFF >> $LOGFILE
    
	# prune
	tail -n $LINES $LOGFILE > $LOGFILE.tmp && mv $LOGFILE.tmp $LOGFILE
    fi
else
    lin_reg
fi

