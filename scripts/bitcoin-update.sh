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
UPNP=- # 0 means build with the lib, but don't start by default
while getopts AaBCcDEFfGgHIjKkLlMmnOoPpSTUuVXxYyz opt; do
    case "$opt" in
	A) PROJECT=aeon ;;
	a) PROJECT=AuroraCoin ;;
	B) PROJECT=blakecoin ;;
	C) CHECKOUT=true ;;
	c) PROJECT=chncoin ;;
	D) PROJECT=dogecoin ;;
	E) PROJECT=electron ;;
	F) PROJECT=gapcoin ;;
	f) FORCE=true ;;
	G) PROJECT=groestlcoin ;;
	g) PROJECT=shibecoin ;;
	H) PROJECT=photon ;;
	I) PROJECT=riecoin ;;
	j) PROJECT=primio ;;
	K) PROJECT=dash ;;
	k) PROJECT=blakebitcoin ;;
	L) PROJECT=Slothcoin ;;
	l) PROJECT=litecoin ;;
	M) PROJECT=bitmonero ;;
	m) PROJECT=maxcoin ;;
	n) PROJECT=namecoin ;;
	O) PROJECT=boolberry-opencl ;;
	o) PROJECT=boolberry ;;
	P) PROJECT=primecoin ;;
	p) PROJECT=ppcoin ;;
	S) PROJECT=skeincoin ;;
	T) PROJECT=Tjcoin ;;
	U) PROJECT=universalmolecule ;;
	u) UPNP=1 ;;
	V) PROJECT=virtacoin ;;
	X) PROJECT=cryptonite ;;
	x) PROJECT=dirac ;;
	Y) PROJECT=lithium ;;
	y) PROJECT=vertcoin ;;
	z) PROJECT=ExclusiveCoin ;;
    esac
done

BINARY=${PROJECT}d

case $PROJECT in
    AuroraCoin)
	GITURL=https://github.com/baldurodinsson/auroracoin-project
	;;
    aeon)
	GITURL=https://github.com/aeonix/aeon
	# For install only
	BINARY="connectivity_tool aeond simplewallet simpleminer"
	;;
    blakebitcoin)
	GITURL=https://github.com/BlakeBitcoin/BlakeBitcoin
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
	BINARY="connectivity_tool bitmonerod simplewallet simpleminer"
	;;
    boolberry)
	GITURL=https://github.com/cryptozoidberg/boolberry
	# For install only
	BINARY="boolbd simplewallet simpleminer"
	;;
    boolberry-opencl)
	GITURL=https://github.com/mbkuperman/boolberry-opencl.git
	# For install only
	BINARY="boolbd simplewallet simpleminer"
	;;
    cryptonite)
	GITURL=https://github.com/MiniblockchainProject/Cryptonite
	;;
    chncoin)
	#GITURL=https://github.com/CHNCoin/CHNCoin.git
	GITURL=https://github.com/RoadTrain/CHNCoin.git
	;;
    dash)
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
    ExclusiveCoin)
	GITURL=https://github.com/exclusivecoin/Exclusive
	;;
    gapcoin)
	GITURL=https://github.com/gapcoin/gapcoin
	;;
    groestlcoin)
	GITURL=https://github.com/GroestlCoin/groestlcoin
	;;
    litecoin)
	GITURL=https://github.com/litecoin-project/litecoin.git	
	;;
    lithium)
	GITURL=https://github.com/lithiumcoin/lithium
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
	# OpenCL alternative
	#GITURL=https://github.com/madMAx43v3r/xpmserver
	#BINARY=primecoind
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
	#GITURL=https://github.com/thimod/Slothcoin
	GITURL=https://github.com/oldambtster/Slothcoin
	;;
    Tjcoin)
	GITURL=https://github.com/TaojingCoin-pd/TjcoinV2
	;;
    universalmolecule)
	GITURL=https://github.com/universalmol/universalmol
	;;
    vertcoin)
	GITURL=https://github.com/vertcoin/vertcoin
	;;
    virtacoin)
	GITURL=https://github.com/virtacoin/VirtaCoinProject
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
    aeon)
	sed -Ei 's/-Werror//' CMakeLists.txt
	nice make -j$(nproc) CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"

	cd build/release/src
    ;;
    bitmonero)
	# Custom compilers are sometimes problematic here, and
	# ccache/distcc don't seem to take effect anyway
	#nice make $MAKEOPTS CC="$CC" CXX="$CXX" CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"

	# This needs to be cleared if the DB path changes
	rm build/release/CMakeCache.txt
	sed -i "s|/usr/include/db.*|$DB_INCPATH|" cmake/FindBerkeleyDB.cmake
	
	nice make -j$(nproc) CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"

	cd build/release/bin
	;;
    boolberry*)
	sed -i 's/Boost_USE_STATIC_LIBS ON/Boost_USE_STATIC_LIBS OFF/' CMakeLists.txt

	sed -i 's/option (UPNPC_BUILD_STATIC "Build static library" TRUE)/option (UPNPC_BUILD_STATIC "Build static library" FALSE)/' contrib/miniupnpc/CMakeLists.txt

	# warning "_BSD_SOURCE and _SVID_SOURCE are deprecated, use _DEFAULT_SOURCE"
	sed -i 's/_BSD_SOURCE/_DEFAULT_SOURCE/g' contrib/miniupnpc/CMakeLists.txt
	
	# As in bitmonero
	nice make -j$(nproc) CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS"

	cd build/release/src
	;;
    cryptonite|dash|dogecoin|gapcoin|groestlcoin|litecoin|riecoin|skeincoin|virtacoin)
	EXTRACONFIG=""

	case $PROJECT in
	    dogecoin)
		EXTRACONFIG="--with-incompatible-bdb"
		;;
	    gapcoin)
		git submodule init
		git submodule update
		;;
	    skeincoin)
		CFLAGS="$CFLAGS -fPIC"
		;;
	esac
	
	sh autogen.sh

	if [ -z "$(echo $UPNP | grep [01])" ]; then
	    EXTRACONFIG="$EXTRACONFIG --without-miniupnpc"
	fi
	
	./configure AR="$AR" CC="$CC" CXX="$CXX" CFLAGS="$CFLAGS" CXXFLAGS="$CFLAGS" --without-gui $EXTRACONFIG

	chmod u+x share/genbuild.sh src/leveldb/build_detect_platform

	nice make $MAKEOPTS

	cd src
	
	BINARY="${PROJECT}d ${PROJECT}-cli"
	;;
    *)
	cd src

	if [ "$PROJECT" == "ExclusiveCoin" ] && [ ! -d obj/zerocoin ]; then
	    mkdir -p obj/zerocoin
	fi
	
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
	nice make $MAKEOPTS AR="$AR" CC="$CC" CXX="$CXX" CXXFLAGS="$CFLAGS" \
	    OPTFLAGS="$CFLAGS" USE_UPNP=$UPNP $BINARY || exit
	;;
esac

if [ ! -d $INSTALLDIR ]; then
    mkdir -p $INSTALLDIR
fi

if [ "$PROJECT" == "boolberry-opencl" ]; then
    cp $BASEDIR/$PROJECTDIR/src/cl/*.cl $INSTALLDIR/
fi

install -bs $BINARY $INSTALLDIR

# Clean up temps
for FILE in $MYCC $MYCXX; do
    if [ -e "$FILE" ]; then rm $FILE; fi
done
