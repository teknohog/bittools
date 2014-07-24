#!/bin/bash

# by teknohog at iki.fi

# Builds a dynamically linked bitcoin or namecoin daemon.

# Requires: openssl, boost and db, in addition to usual development
# tools.

# This should be easy to extend for the GUI version too, if
# INCLUDEPATHS are adjusted accordingly, and WXLIBS generated using
# wx-config --libs, and WXDEFS using wx-config --cxxflags.

# moved from svn to git on 2011-04-29, releases not implemented for now
# https://github.com/bitcoin/bitcoin

CHECKOUT=false
FORCE=false
PROJECT=bitcoin
UPNP=
while getopts aBCcDEfGgHIjKkLlMmnoPpSTUuVx opt; do
    case "$opt" in
	a) PROJECT=AuroraCoin ;;
	B) PROJECT=blakecoin ;;
	C) CHECKOUT=true ;;
	c) PROJECT=chncoin ;;
	D) PROJECT=dogecoin ;;
	E) PROJECT=electron ;;
	f) FORCE=true ;;
	G) PROJECT=GroestlCoin ;;
	g) PROJECT=shibecoin ;;
	H) PROJECT=photon ;;
	I) PROJECT=riecoin ;;
	j) PROJECT=primio ;;
	K) PROJECT=darkcoin ;;
	k) PROJECT=blakebitcoin ;;
	L) PROJECT=Slothcoin ;;
	l) PROJECT=litecoin ;;
	M) PROJECT=bitmonero ;;
	m) PROJECT=maxcoin ;;
	n) PROJECT=namecoin ;;
	o) PROJECT=boolberry ;;
	P) PROJECT=primecoin ;;
	p) PROJECT=ppcoin ;;
	S) PROJECT=skeincoin ;;
	T) PROJECT=Tjcoin ;;
	U) PROJECT=universalmolecule ;;
	u) UPNP=1 ;;
	V) PROJECT=virtacoin ;;
	x) PROJECT=dirac ;;
    esac
done

BINARY=${PROJECT}d

case $PROJECT in
    AuroraCoin)
	GITURL=https://github.com/baldurodinsson/auroracoin-project
	;;
    blakebitcoin)
	GITURL=https://github.com/BlueDragon747/BlakeBitcoin
	;;
    blakecoin)
	GITURL=https://github.com/BlueDragon747/Blakecoin.git
	;;
    bitcoin)
	GITURL=https://github.com/bitcoin/bitcoin.git
	;;
    bitmonero)
	GITURL=https://github.com/monero-project/bitmonero
	# For install only
	BINARY="bitmonerod simplewallet simpleminer"
	;;
    boolberry)
	GITURL=https://github.com/cryptozoidberg/boolberry
	# For install only
	BINARY="boolbd simplewallet simpleminer"
	;;
    chncoin)
	#GITURL=https://github.com/CHNCoin/CHNCoin.git
	GITURL=https://github.com/RoadTrain/CHNCoin.git
	;;
    darkcoin)
	GITURL=https://github.com/darkcoinproject/darkcoin
	;;
    dirac)
	GITURL=https://github.com/bryceweiner/Dirac
	;;
    dogecoin)
	GITURL=https://github.com/dogecoin/dogecoin.git
	;;
    electron)
	GITURL=https://github.com/Electron-Coin2014/Electron-ELT
	;;
    GroestlCoin)
	GITURL=https://github.com/GroestlCoin/GroestlCoin
	;;
    litecoin)
	GITURL=https://github.com/litecoin-project/litecoin.git	
	;;
    maxcoin)
	GITURL=https://github.com/Max-Coin/maxcoin
	;;
    namecoin)
	GITURL=https://github.com/namecoin/namecoin.git
	;;
    photon)
	GITURL=https://github.com/photonproject/photon
	;;
    ppcoin)
	GITURL=https://github.com/ppcoin/ppcoin.git
	;;
    primecoin)
	#GITURL=https://github.com/primecoin/primecoin.git
	#GITURL=https://github.com/Chemisist/primecoin.git
	#GITURL=https://github.com/mikaelh2/primecoin.git
	GITURL=https://bitbucket.org/mikaelh/primecoin-hp.git
	;;
    primio)
	GITURL=https://github.com/Primio/Primio
	;;
    riecoin)
	GITURL=https://github.com/riecoin/riecoin
	;;
    shibecoin)
	GITURL=https://github.com/cryptoshock/shibecoin
	;;
    skeincoin)
	GITURL=https://github.com/skeincoin/skeincoin.git
	;;
    Slothcoin)
	GITURL=https://github.com/thimod/Slothcoin
	;;
    Tjcoin)
	GITURL=https://github.com/TaojingCoin-pd/TjcoinV2
	;;
    universalmolecule)
	GITURL=https://github.com/universalmol/universalmol
	;;
    virtacoin)
	GITURL=https://github.com/virtacoin/VirtaCoinProject
	# For install only
	BINARY="virtacoind virtacoin-cli"
	;;
    *)
	exit
	;;
esac

# Sometimes different from PROJECT (binary etc.) name, comes from the
# git repo
PROJECTDIR=$(echo $GITURL | sed -Ee 's|.*/([^/.]*)(.git)?$|\1|')

BASEDIR=~/sources
INSTALLDIR=~/distr.projects/$PROJECT-git/

# Compiler options, in preference:
# 1. environment, 2. Gentoo make.conf if found, 3. defaults below

for FILE in /etc/portage/make.conf /etc/make.conf; do
    if [ -f $FILE ]; then
	MAKECONF=$FILE
	break
    fi
done

if [ -f $MAKECONF ]; then
    for i in CFLAGS FEATURES MAKEOPTS; do
	# There must be a more elegant way to see if $i is set, but
	# this will do for now
	if [ -z "`set | grep $i=`" ]; then
	    eval "`grep ^$i= $MAKECONF`"
	fi
    done

    CCACHE=""
    DISTCC=""
    if [ -n "`echo $FEATURES | grep ccache`" ]; then CCACHE="ccache"; fi
    if [ -n "`echo $FEATURES | grep distcc`" ]; then DISTCC="distcc"; fi
    
    CC="${CC:-$CCACHE $DISTCC $MACHTYPE-gcc}"
    CXX="${CXX:-$CCACHE $DISTCC $MACHTYPE-g++}"
fi
  
# Revert to these defaults, if not defined so far
CFLAGS="${CFLAGS:--O2 -pipe -march=native}"
AR="${AR:-$MACHTYPE-ar}"
CC="${CC:-$MACHTYPE-gcc}"
CXX="${CXX:-$MACHTYPE-g++}"
MAKEOPTS="${MAKEOPTS:--j`nproc`}"

# find the latest version
DB_INCPATH=`find /usr/include/ -name db_cxx.h | xargs -n1 dirname | sort | tail -n1`

CFLAGS="$CFLAGS -I/usr/include -I$DB_INCPATH"

if $CHECKOUT || [ ! -d $BASEDIR/$PROJECTDIR ]; then
    cd $BASEDIR
    rm -rf $PROJECTDIR
    git clone $GITURL || exit
    cd $PROJECTDIR
else
    cd $BASEDIR/$PROJECTDIR

    if [ -e CMakeLists.txt ]; then
	# CMakeLists.txt cannot be updated if we changed it
	git stash save
    fi

    # Do not build if there is no source update, but force build from
    # command line if wanted anyway
    STATUSFILE=`mktemp /tmp/XXXXXX.txt`
    git pull | tee $STATUSFILE
    NOUPDATE="`grep Already.up-to-date $STATUSFILE`"
    ERROR="`file $STATUSFILE | grep empty`"
    rm $STATUSFILE
    if ( [ -n "$NOUPDATE" ] || [ -n "$ERROR" ] ) && ! $FORCE; then
	exit
    fi
fi

# leveldb is broken by multi-part compiler names like
# "ccache distcc g++"... and so is bitmonero, so fix this for everyone
if [ "`echo $CXX | wc -w`" -gt 1 ]; then

    MYCC=`mktemp`
    MYCXX=`mktemp`

    cat<<EOF > $MYCC
#!/bin/bash
exec $CC "\$@"
EOF

    cat<<EOF > $MYCXX
#!/bin/bash
exec $CXX "\$@"
EOF

    for FILE in $MYCC $MYCXX; do
	chmod 700 $FILE
    done

    CC=$MYCC
    CXX=$MYCXX
fi

case $PROJECT in
    bitmonero|boolberry)
	if [ -z "`grep Boost_LIBRARIES CMakeLists.txt | grep pthread`" ]; then
	    # undefined reference to symbol
	    # 'pthread_mutexattr_settype@@GLIBC_2.2.5' -- fix borrowed
	    # from Monero
	    sed -i 's/set(Boost_LIBRARIES.*/set(Boost_LIBRARIES "${Boost_LIBRARIES};rt;pthread")/' CMakeLists.txt
	fi

	# "# Note that at the time of this writing the
	# -Wstrict-prototypes flag added below will make this fail"
	sed -i 's/find_package(Threads REQUIRED)//' CMakeLists.txt

	sed -i 's/Boost_USE_STATIC_LIBS ON/Boost_USE_STATIC_LIBS OFF/' CMakeLists.txt

	# Custom compilers are sometimes problematic here, and
	# ccache/distcc don't seem to take effect anyway
	#nice make $MAKEOPTS CC="$CC" CXX="$CXX" CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"
	nice make -j`nproc` CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"

	cd build/release/src
	;;
    virtacoin)
	sh autogen.sh

	./configure AR="$AR" CC="$CC" CXX="$CXX" CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"
	chmod u+x share/genbuild.sh src/leveldb/build_detect_platform

	nice make $MAKEOPTS

	cd src
	;;
    *)
	cd src
	
	# Some implementations are missing executable perms
	LDB=leveldb/build_detect_platform
	if [ -e $LDB ] && [ ! -x $LDB ]; then
	    chmod u+x $LDB
	fi
	
	cp makefile.unix Makefile

	if [ "$PROJECT" == "Tjcoin" ]; then
	    sed -i 's/litecoin/Tjcoin/g' Makefile
	    sed -i 's/scrypt.o/ocean.o/g' Makefile
	fi
    
	sed -i 's/-O[23]/\$(OPTFLAGS)/g' Makefile
	sed -i 's/g++/\$(CXX)/g' Makefile
	sed -i 's/Bstatic/Bdynamic/g' Makefile
	
	# The general case should work with Blakecoin too
	sed -i 's/db_cxx-5.1/db_cxx/g' Makefile
	
	# *sigh* everyone uses x86?
	if [ -z "`echo $MACHTYPE | grep 86`" ]; then
	    sed -i 's/-msse2//g' Makefile
	    sed -i 's/-DFOURWAYSSE2//g' Makefile
	    sed -i 's/-march=amdfam10//g' Makefile
	fi    
	
	# Help Intel compilers with linking
	sed -i 's/-l /-l/g' Makefile
	
	# Missing on Primio
	if [ ! -d obj ]; then
	    mkdir obj
	fi
	
	make clean
	nice make $MAKEOPTS AR="$AR" CC="$CC" CXX="$CXX" \
	    OPTFLAGS="$CFLAGS" USE_UPNP=$UPNP $BINARY || exit
	;;
esac

if [ ! -d $INSTALLDIR ]; then
    mkdir -p $INSTALLDIR
fi
install -bs $BINARY $INSTALLDIR

# Clean up temps
for FILE in $MYCC $MYCXX; do
    if [ -e "$FILE" ]; then rm $FILE; fi
done
