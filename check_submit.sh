#! /bin/bash

assignment=${1:?1st argument must be short name of assignment}
arch=${2:?2nd argument must be name of submitted archive}
warncheck=${3:-yes}
CC=${CC:-clang -std=c11}

set -ex

die() {
    echo "$@" >&2
    exit 1
}

base=${arch%%.*}
: if the following fails, the archive base name is incorrect
test x"$base" = x$assignment

ext=${arch#*.}
case $ext in
    tar) fmt= ;;
    tar.gz | tgz) fmt=z ;;
    tar.bz2 | tbz) fmt=j ;;
    tar.xz | txz) fmt=J ;;
    *) die "unknown archive format" ;;
esac
: if the following fails, tar cannot read the archive
tar -t${fmt}f "$arch" >/dev/null

tmpd=$(mktemp -d -t test)
tar -C "$tmpd" -x${fmt}f "$arch"
cd "$tmpd"

: if the following fails, the archive does not contain a properly named directory
test -d "$base"

: the archive must not contain anything else
test -e .svn && exit 1
test -e .git && exit 1
test -e .DS_Store && exit 1
for i in *; do
    if test x"$i" = x"$base"; then continue; fi
    exit 1
done

cd "$base"

: AUTHORS must exist and be readable
test -r AUTHORS

: AUTHORS must contain VUnetIDs
re='[a-z][a-z][a-z][0-9][0-9][0-9]'
students=$(grep "$re" < AUTHORS | sed -e 's/^.*\('"$re"'\).*$/\1/g')
test x"$students" != x

: archive must not contain generated files
f=$(find . -name "*.[oisa]" -or -name \*.bak -or -name \*~ -or -name "#*#")
test x"$f" = x

: source files must be readable and not executable
for i in Makefile *.[hcS]; do
  if test -e "$i"; then test -r "$i" -a -f "$i" -a \! -x "$i"; fi
done

: if 'configure' exists, it must be executable
if test -e configure; then test -f configure -a -x configure; fi

: Makefile if exists must contain targets all and clean
if test -r Makefile; then
    make -n clean
    make -n all
    : default target must be same as "all"
    make -n &>../log.default
    make -n all &>../log.all
    diff ../log.default ../log.all
fi

: C sources must exist and must be compilable without arguments
cs=$(find . -name "*.[cS]")
test x"$cs" != x

case $warncheck in
  yes) warn="-Werror -Wall -Wextra -O -Wuninitialized -Winit-self -Wswitch-enum -Wdeclaration-after-statement -Wshadow -Wpointer-arith -Wcast-qual -Wcast-align -Wwrite-strings -Wconversion -Waggregate-return -Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations -Wredundant-decls -Wnested-externs -Wno-long-long" ;;
  *) warn= ;;
esac

$CC -I. $warn -c *.[cS]

: all first-level tests passed, perhaps the submission is good
