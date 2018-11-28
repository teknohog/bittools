#!/bin/bash

# by teknohog

# Collect recent difficulty statistics for the given coin using the -s
# option. By default, show the average of last $LINES entries.

LINES=24

function check_stale() {
    # 2018-11-24 Separated as it's useful for $SET too
    
    # 2017-08-24 As in Python bittools
    MTIME=$(date +%s -r $LOGFILE)
    NOW=$(date +%s)
    if [ $((NOW - MTIME)) -gt 10000 ]; then
	echo Warning: stale logfile
	echo
    fi
}

function lin_reg () {
    # Use uniq to avoid dupes; the file should already be sorted

    check_stale
    
    if $VERBOSE; then
	uniq $LOGFILE
	echo
    fi
    
    # Linear regression to estimate a current diff
    uniq $LOGFILE | tail -n $LINES | \
	awk '{n = n + 1
sx = sx + $1
sy = sy + $2
sxy = sxy + $1*$2
sx2 = sx2 + $1**2
sy2 = sy2 + $2**2}
END{b = (n*sxy - sx*sy) / (n*sx2 - sx**2)
a = (sy - b*sx) / n
avg = sy/n
estimate = a + b*systime()
r = (n*sxy - sx*sy) / ((n*sx2 - sx**2)*(n*sy2 - sy**2))**0.5
print "correlation " r
print "pct_hourly " b/avg * 3600 * 100
print "average " avg
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
while getopts 2AaBcDEFGgHIJjKLlMmnOoPpSsTUVvwXxYyZz opt; do
    case "$opt" in
	2) PROJECT=btcp ;;
	A) PROJECT=aeon ;;
	#a) PROJECT=AuroraCoin ;;
	a) PROJECT=zen ;;
	B) PROJECT=blakecoin ;;
	#c) PROJECT=chncoin ;;
	c) PROJECT=ethereum-classic ;;
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
	J) PROJECT=vcash ;;
	j) PROJECT=primio ;;
	K) PROJECT=dash ;;
	L) PROJECT=Slothcoin ;;
	l) PROJECT=litecoin ;;
	M) PROJECT=monero ;;
	m) PROJECT=maxcoin ;;
	n) PROJECT=namecoin ;;
	O|o)
	    # The -O distinction for boolberry-opencl only matters for
	    # building binaries
	    PROJECT=boolberry
	    ;;
	P) PROJECT=primecoin ;;
	p)
	    PROJECT=peercoin
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
	Z) PROJECT=zcash ;;
	z)
	    #PROJECT=ExclusiveCoin
	    #POS=true
	    PROJECT=zcoin
	    ;;
    esac
done

case $PROJECT in
    boolberry)
	LOGFILE=~/.boolb/difflog
	;;
    btcp)
	LOGFILE=~/.btcprivate/difflog
	;;
    ethereum-classic)
	LOGFILE=~/.$PROJECT/mainnet/difflog
	;;
    monero)
	LOGFILE=~/.bitmonero/difflog
	;;
    shibecoin)
	LOGFILE=~/.ShibeCoin/difflog
	;;
    Tjcoin)
	LOGFILE=~/.TjcoinV2/difflog
	;;
    vcash)
	LOGFILE=~/.Vcash/difflog
	;;
    *)
	LOGFILE=~/.$PROJECT/difflog
	;;
esac

if $SET; then
    # 2016-01-15
    case $PROJECT in
	boolberry)
	    PROCESS=boolbd
	    ;;
	ethereum*)
	    PROCESS=geth
	    ;;
	*)
	    PROCESS=${PROJECT}d
	    ;;
    esac

    # pgrep fails for names > 15 chars
    if [ -z "$(ps ax | grep $PROCESS | grep -v grep)" ]; then
	exit 0
    fi
    
    # top up the logfile
    case $PROJECT in
	aeon|monero|boolberry)
	    DIFF=$(cnfo.py --$PROJECT | grep -m1 difficulty | awk '{print $2}')
	    ;;
	ethereum*)
	    if [ "$PROJECT" == "ethereum-classic" ]; then
		COPT="-c"
	    fi
	    DIFF=$(etherinfo.py $COPT | grep -m1 difficulty | awk '{print $2}')
	    ;;
	vcash)
	    DIFF=$(coinfo.py -J | grep -m1 difficulty | awk '{print $2}')
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

    # 2018-11-24 Remove stale entries; simple by removing the file itself
    check_stale | grep -i stale && rm $LOGFILE
    
    # don't ruin the difflog if we have problems

    # 2018-08-09 Zero diff is an error that sometimes comes out of RPC
    # scripts, and ruins meandiff calculations. Need integer for Bash
    # comparison.
    DIFF_INT=${DIFF//\.*/}
    
    if [ -n "$DIFF" ] && [ $DIFF_INT -gt 0 ]; then
	TIME=$(date +%s)
	echo $TIME $DIFF >> $LOGFILE
    
	# prune
	tail -n $LINES $LOGFILE > $LOGFILE.tmp && mv $LOGFILE.tmp $LOGFILE
    fi
else
    lin_reg
fi
