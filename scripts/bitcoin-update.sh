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
while getopts bCcflnPpr:u opt; do
    case "$opt" in
	b) PROJECT=blakecoin ;;
	c) PROJECT=chncoin ;;
	C) CHECKOUT=true ;;
	f) FORCE=true ;;
	l) PROJECT=litecoin ;;
	n) PROJECT=namecoin ;;
	P) PROJECT=primecoin ;;
	p) PROJECT=ppcoin ;;
	r) REVISION=$OPTARG ;;
	u) UPNP=1 ;;
    esac
done

PROJECTDIR=$PROJECT
case $PROJECT in
    blakecoin)
	GITURL=https://github.com/BlueDragon747/Blakecoin.git
	PROJECTDIR=Blakecoin
	;;
    bitcoin)
	GITURL=https://github.com/bitcoin/bitcoin.git
	;;
    chncoin)
	#GITURL=https://github.com/CHNCoin/CHNCoin.git
	GITURL=https://github.com/RoadTrain/CHNCoin.git
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
    primecoin)
	#GITURL=https://github.com/primecoin/primecoin.git
	#GITURL=https://github.com/Chemisist/primecoin.git
	#GITURL=https://github.com/mikaelh2/primecoin.git
	GITURL=https://bitbucket.org/mikaelh/primecoin-hp.git
	PROJECTDIR=primecoin-hp
	;;
    *)
	exit
	;;
esac

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
    NOUPDATE="`grep Already.up-to-date $STATUSFILE`"
    ERROR="`file $STATUSFILE | grep empty`"
    rm $STATUSFILE
    if ( [ -n "$NOUPDATE" ] || [ -n "$ERROR" ] ) && ! $FORCE; then
	exit
    fi
fi

cd src

cp makefile.unix Makefile
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

# leveldb is broken by multi-part compiler names like
# "ccache distcc g++"
#sed -i 's/CXX=$(CXX)/CXX="$(CXX)"/' leveldb/Makefile
# The scripts need more fixing, so work around multi-part names for now
if [ -n "`grep ^leveldb/libleveldb.a: Makefile`" ] && \
    [ "`echo $CXX | wc -w`" -gt 1 ]; then

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

    # Also, some implementations are missing executable perms
    chmod u+x leveldb/build_detect_platform
fi

# Help Intel compilers with linking
sed -i 's/-l /-l/g' Makefile

make clean
nice make $MAKEOPTS AR="$AR" CC="$CC" CXX="$CXX" \
    OPTFLAGS="$CFLAGS" USE_UPNP=$UPNP $BINARY || exit

if [ ! -d $INSTALLDIR ]; then
    mkdir -p $INSTALLDIR
fi
install -bs $BINARY $INSTALLDIR

# Clean up temps
for FILE in $MYCC $MYCXX; do
    if [ -e "$FILE" ]; then rm $FILE; fi
done
