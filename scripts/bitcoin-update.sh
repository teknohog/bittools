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
UPNP=
while getopts Ccflnpr:u opt; do
    case "$opt" in
	c) PROJECT=chncoin ;;
	C) CHECKOUT=true ;;
	f) FORCE=true ;;
	l) PROJECT=litecoin ;;
	n) PROJECT=namecoin ;;
	p) PROJECT=ppcoin ;;
	r) REVISION=$OPTARG ;;
	u) UPNP=1 ;;
    esac
done

PROJECTDIR=$PROJECT
case $PROJECT in
    bitcoin)
	GITURL=https://github.com/bitcoin/bitcoin.git
	;;
    chncoin)
	GITURL=https://github.com/CHNCoin/CHNCoin.git
	PROJECTDIR=CHNCoin
	;;
    litecoin)
	GITURL=https://github.com/litecoin-project/litecoin.git	
	;;
    namecoin)
	GITURL=https://github.com/namecoin/namecoin.git
	;;
    ppcoin)
	GITURL=https://github.com/ppcoin/ppcoin.git
	;;
    *)
	exit
	;;
esac

BASEDIR=~/sources
INSTALLDIR=~/distr.projects/$PROJECT-git/

# On Gentoo, compiler options are automatically found. Otherwise they
# can be specified manually below.

for FILE in /etc/portage/make.conf /etc/make.conf; do
    if [ -f $FILE ]; then
	MAKECONF=$FILE
	break
    fi
done

if [ -f $MAKECONF ]; then
    for i in CFLAGS FEATURES MAKEOPTS; do
	eval "`grep ^$i= $MAKECONF`"
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

CFLAGS="$CFLAGS -I/usr/include -I$DB_INCPATH"

BINARY=${PROJECT}d

if $CHECKOUT || [ ! -d $BASEDIR/$PROJECTDIR ]; then
    if [ -n "$REVISION" ]; then
	REVISION=@$REVISION
    fi
    cd $BASEDIR
    rm -rf $PROJECTDIR
    git clone $GITURL || exit
    cd $PROJECTDIR
else
    if [ -n "$REVISION" ]; then
	REVISION="-r $REVISION"
    fi

    cd $BASEDIR/$PROJECTDIR

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

# *sigh* everyone uses x86?
if [ -z "`echo $MACHTYPE | grep 86`" ]; then
    sed -i 's/-msse2//g' Makefile
    sed -i 's/-DFOURWAYSSE2//g' Makefile
    sed -i 's/-march=amdfam10//g' Makefile
fi    

# leveldb is broken by multi-part compiler names like
# "ccache distcc g++"
#sed -i 's/CXX=$(CXX)/CXX="$(CXX)"/' leveldb/Makefile
# The scripts need more fixing, so disable ccache/distcc for now
if [ $PROJECT == "bitcoin" ]; then
    CXX="$MACHTYPE-g++"
    MAKEOPTS="-j2"
fi

make clean
nice make $MAKEOPTS CXX="$CXX" OPTFLAGS="$CFLAGS" USE_UPNP=$UPNP \
    $BINARY || exit

if [ ! -d $INSTALLDIR ]; then
    mkdir -p $INSTALLDIR
fi
install -bs $BINARY $INSTALLDIR
