#!/usr/bin/env bash
# Package overwrite_regex/ as dist/overwrite_regex-<version>.7z, laid out the
# way MO2 expects: the archive's top-level folder is plugins/.
set -euo pipefail
cd "$(dirname "$0")"

version=$(grep -m1 '^version = ' pyproject.toml | cut -d'"' -f2)
archive="dist/overwrite_regex-$version.7z"

rm -rf plugins
mkdir -p plugins dist
cp -r overwrite_regex plugins/
rm -f "$archive"
'/mnt/c/Program Files/7-Zip/7z.exe' a "$archive" plugins -xr'!__pycache__' >/dev/null
rm -rf plugins

echo "$archive"
