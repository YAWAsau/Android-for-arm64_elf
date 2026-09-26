#!/usr/bin/env bash
set -euo pipefail
cd "$1"
cd busybox
cp ../busybox.config .config
# Empty answers accept upstream defaults; new applets are pinned off in the supplied config.
set +o pipefail
yes '' | make oldconfig > ../configure.log 2>&1
config_status=${PIPESTATUS[1]}
set -o pipefail
if [ "$config_status" != 0 ]; then cat ../configure.log; exit "$config_status"; fi
gcc applets/applet_tables.c -o applets/applet_tables
applets/applet_tables include/applet_tables.h include/NUM_APPLETS.h
gcc applets/usage.c -o applets/usage -Iinclude
applets/usage_compressed include/usage_compressed.h applets
scripts/mkconfigs include/bbconfigopts.h include/bbconfigopts_bz2.h
scripts/generate_BUFSIZ.sh include/common_bufsiz.h
srctree="$PWD" HOSTCC=gcc scripts/embedded_scripts include/embedded_scripts.h embed applets_sh
cd ..
python3 generate-makefile.py
