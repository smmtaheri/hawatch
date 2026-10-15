#!/bin/sh
set -eu

build_root="${HAWATCH_FRONTEND_BUILD_ROOT:-/usr/share/nginx/html}"
asset_root="${HAWATCH_FRONTEND_ASSETS_ROOT:-/var/lib/hawatch-frontend}"
case "$asset_root" in /*) ;; *) echo 'Frontend asset root must be absolute' >&2; exit 1;; esac
case "$asset_root" in /|/home|/root|/usr|/var|/tmp) echo 'Refusing broad frontend asset root' >&2; exit 1;; esac

for namespace in static-assets static-public; do
  mkdir -p "$asset_root/$namespace"
  for source in "$build_root/$namespace/"*; do
    [ -d "$source" ] || continue
    version="${source##*/}"
    case "$version" in ''|*[!A-Za-z0-9_-]*) echo 'Invalid frontend asset version' >&2; exit 1;; esac
    destination="$asset_root/$namespace/$version"
    if [ ! -d "$destination" ] || [ "$version" = local ]; then
      mkdir -p "$destination"
      if [ "$namespace" = static-assets ]; then
        cp -a "$source/assets" "$destination/"
        # Publish the preload graph only after all files it names are available.
        cp "$source/page-assets.json" "$destination/.page-assets.json.tmp"
        mv "$destination/.page-assets.json.tmp" "$destination/page-assets.json"
      else
        cp -a "$source/." "$destination/"
      fi
    fi
    touch "$destination"
  done
  # Bound disk usage: five small JS/CSS releases and two independently-versioned
  # public asset releases. This is not a database or application backup.
  keep=5
  [ "$namespace" != static-public ] || keep=2
  ls -1dt "$asset_root/$namespace/"* | awk -v keep="$keep" 'NR > keep' | while IFS= read -r old; do
    [ -d "$old" ] || continue
    case "${old##*/}" in ''|*[!A-Za-z0-9_-]*) exit 1;; esac
    case "$old" in "$asset_root/$namespace/"*) rm -rf -- "$old";; *) exit 1;; esac
  done
done
