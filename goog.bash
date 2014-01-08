#!/bin/bash

goog=/misc/space/music/goog

mkdir -p $goog
cd $goog
rm -f [0-9].* [0-9][0-9].* [0-9][0-9][0-9].* [0-9][0-9][0-9][0-9].*
find /misc/space/music/master -type f \( -name \*.mp3 -o -name \*.ogg -o -name \*.flac \) | \
    for ((x=0;; x++)); do
        read src || break
        ln -v "$src" "$x.${src##*.}"
    done
