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
REVISION=""
while getopts cflnr: opt; do
    case "$opt" in
	c) CHECKOUT=true ;;
	f) FORCE=true ;;
	l) PROJECT=litecoin ;;
	n) PROJECT=namecoin ;;
	r) REVISION=$OPTARG ;;
    esac
done

case $PROJECT in
    bitcoin)
	GITURL=https://github.com/bitcoin/bitcoin.git
	;;
    litecoin)
	GITURL=https://github.com/litecoin-project/litecoin.git	
	;;
    namecoin)
	GITURL=https://github.com/namecoin/namecoin.git
	;;
    *)
	exit
	;;
esac

BASEDIR=~/sources
INSTALLDIR=~/distr.projects/$PROJECT-git/

# On Gentoo, compiler options are automatically found. Otherwise they
# can be specified manually below.

if [ -f /etc/make.conf ]; then
    for i in CFLAGS FEATURES MAKEOPTS; do
	eval "`grep ^$i= /etc/make.conf`"
    done
    
    CCACHE=""
    DISTCC=""
    if [ -n "`echo $FEATURES | grep ccache`" ]; then CCACHE="ccache"; fi
    if [ -n "`echo $FEATURES | grep distcc`" ]; then DISTCC="distcc"; fi
    
    CXX="$CCACHE $DISTCC $MACHTYPE-g++"
else
    # Manual settings
    CFLAGS="-O2 -pipe -march=native"
    CXX="$MACHTYPE-g++"
    MAKEOPTS="-j2"
fi

# find the latest version
DB_INCPATH=`find /usr/include/ -name db_cxx.h | xargs -n1 dirname | sort | tail -n1`

# svn 251 / bitcoin 0.3.21 no more has INCLUDEPATHS, so merge this
# with optimizations
#INCLUDEPATHS="-I/usr/include -I$DB_INCPATH"
CFLAGS="$CFLAGS -I/usr/include -I$DB_INCPATH"

BINARY=${PROJECT}d

if $CHECKOUT || [ ! -d $BASEDIR/$PROJECT ]; then
    if [ -n "$REVISION" ]; then
	REVISION=@$REVISION
    fi
    cd $BASEDIR
    rm -rf $PROJECT
    git clone $GITURL || exit
    cd $PROJECT
else
    if [ -n "$REVISION" ]; then
	REVISION="-r $REVISION"
    fi

    cd $BASEDIR/$PROJECT

    # Do not build if there is no source update, but force build from
    # command line if wanted anyway
    STATUSFILE=`mktemp /tmp/XXXXXX.txt`
    git pull | tee $STATUSFILE
    NOUPDATE="`grep Already.up-to-date. $STATUSFILE`"
    rm $STATUSFILE
    if [ -n "$NOUPDATE" ] && ! $FORCE; then
	exit
    fi
fi

cd src

cp makefile.unix Makefile
sed -i 's/-O2/\$(OPTFLAGS)/g' Makefile
sed -i 's/g++/\$(CXX)/g' Makefile
sed -i 's/Bstatic/Bdynamic/g' Makefile

# forum: "Remove that. Else the SHA256_Transform will return the initstate."
sed -i 's/-DCRYPTOPP_DISABLE_SSE2//g' Makefile

# compiler memory hogging? seems to hog with or without
#sed -i 's/-O3//g' Makefile

# *sigh* everyone uses x86?
if [ -z "`echo $MACHTYPE | grep 86`" ]; then
    sed -i 's/-msse2//g' Makefile
    sed -i 's/-DFOURWAYSSE2//g' Makefile
    sed -i 's/-march=amdfam10//g' Makefile
fi    

# march conflict and/or -march=atom bug with gcc 4.5.1? This is a
# segfault in libstdc++, which was compiled for core2, so the conflict
# may lie there. With gcc 4.5.2, the problem persists; it only crashes
# when mining, though, with this line in debug:
# CPUID 6c65746e family 6, model 28, stepping 10, fUseSSE2=1
if [ -n "`echo $CFLAGS | grep atom`" ]; then
    sed -i 's/-march=amdfam10//g' Makefile
    CFLAGS=${CFLAGS//march=atom/march=core2}
#    CFLAGS=${CFLAGS//mtune=atom/mtune=core2}
fi

# This might help for PPC et al, but it probably requires all the
# libraries in little-endian form as well... not impossible with
# static linking, though the libraries must be built separately

# sed -i 's/\$(OPTFLAGS)/\$(OPTFLAGS) -mlittle-endian/g' Makefile

# disable upnp by setting the variable to null (nothing, not zero)
make clean
nice make $MAKEOPTS CXX="$CXX" OPTFLAGS="$CFLAGS" USE_UPNP= \
    INCLUDEPATHS="$INCLUDEPATHS" $BINARY || exit

if [ ! -d $INSTALLDIR ]; then
    mkdir -p $INSTALLDIR
fi
install -bs $BINARY $INSTALLDIR
