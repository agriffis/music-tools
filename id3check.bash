#!/bin/bash

if [[ $1 == --fix ]]; then
    fix=true
    shift
else
    fix=false
fi

get() {
    declare x
    x=${2#*=== $1*: }
    if [[ "$x" == "$2" ]]; then
        return
    else
        echo "${x%%$'\n'*}"
    fi
}

find "$@" -name \*.mp3 | while read f; do
    f=${f#./}
    artist=${f%%/*}
    album=${f#*/}
    album=${album%%/*}
    title=${f##*/}
    title=${title%.mp3}
    if [[ $title == [0-9]\ * || $title == [0-9][0-9]\ * ]]; then
        track=${title%% *}
        title=${title#* }
    elif [[ $title == [0-9].mp3 || $title == [0-9][0-9].mp3 ]]; then
        track=${title%.mp3}
        title=
    else
        track=
    fi

    info=$(id3info "$f")
    artist_=$(get TPE1 "$info")
    album_=$(get TALB "$info")
    track_=$(get TRCK "$info")
    title_=$(get TIT2 "$info")

    if [[ "$artist" != "$artist_" ||
        "$album" != "$album_" ||
        "$track" != "$track_" ||
        "$title" != "$title_" ]]
    then
        echo "$f"
        if [[ "$artist" != "$artist_" ]]; then
            echo "  Artist: $artist_"
        fi
        if [[ "$album" != "$album_" ]]; then
            echo "  Album: $album_"
        fi
        if [[ "$track" != "$track_" ]]; then
            echo "  Track: $track_"
        fi
        if [[ "$title" != "$title_" ]]; then
            echo "  Title: $title_"
        fi

        if $fix; then
            echo "  FIXING"
            ( set -x
              id3v2 -a "$artist" -A "$album" -T "$track" -t "$title" "$f"
            )
        fi
    fi
done
