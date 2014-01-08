#!/bin/bash

main() {
    master=/misc/space/music/master
    mp3=/misc/space/music/mp3

    if [[ $# == 0 ]]; then
        set -- "$master"
    fi

    set -e

    find "$@" ! -type d ! -path '*/[.@]*' | sort | while read src; do
        [[ $src == "$master"/* ]]
        dest="${src#$master/}"
        [[ $dest != "$master"/* ]]
        dest="$mp3/${dest/%.flac/.mp3}"

        [[ ! -e "$dest" ]] || continue

        mkdir -pv "${dest%/*}"

        if [[ $src == *.flac ]]; then
            (set -x; flac -dc "$src" | lame -v - "$dest")
            copy-tags "$src" "$dest"
        else
            ln -sv "$src" "$dest"
        fi
    done

    symlinks -c -d -r "$mp3"
}

declare -A id3v1genres
while read n s; do
    n=${n%:}
    id3v1genres["$(tr A-Z a-z <<<"$s")"]=$n
done <<<"$(id3v2 -L)"

copy-tags() {
    declare ARTIST ALBUM TITLE DATE GENRE TRACKNUMBER

    eval "$(metaflac --export-tags-to=- "$1" | \
        sed "s/'/'\\\\''/g" | \
        sed "s/=/='/" | \
        sed "s/\$/'/")"

    if [[ $DATE != ???? ]]; then
        unset DATE
    fi

    if [[ -n $GENRE ]]; then
        GENRE=$(tr A-Z a-z <<<"$GENRE")
        GENRE=${id3v1genres["$GENRE"]}
    fi

    (set -x
    id3v2 -a "$ARTIST" -A "$ALBUM" -t "$TITLE" -T "$TRACKNUMBER" \
        ${DATE:+-y "$DATE"} ${GENRE:+-g "$GENRE"} "$2"
    )
}

main "$@"
