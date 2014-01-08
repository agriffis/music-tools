#!/usr/bin/env python3

from itertools import chain
import re
import os
import shutil
import subprocess
from subprocess import Popen, PIPE, DEVNULL


def convert_to_mp3(input_filename, output_filename):
    assert os.path.lexists(input_filename)
    assert not os.path.lexists(output_filename)

    p1 = Popen(['flac', '-dc', input_filename], stdin=DEVNULL, stdout=PIPE)
    p2 = Popen(['lame', '-v', '-', output_filename], stdin=p1.stdout)
    p1.stdout.close()  # so p1 gets SIGPIPE if p2 exits
    status = p2.wait()

    if status != 0:
        raise subprocess.CalledProcessError("lame returned exit status {}".format(status))


def symlink_to_mp3(input_filename, output_filename):
    assert os.path.lexists(input_filename)
    assert not os.path.lexists(output_filename)

    os.symlink(input_filename, output_filename)


def tidy_symlinks(path):
    subprocess.call(['symlinks', '-c', '-d', '-r', path])


def clean_filename(name):
    assert '/' not in name
    name = re.sub(r'[^-. \w]', '_', name)
    name = re.sub(r'\.flac$', '.mp3', name, re.I)
    return name


def is_newer_than(this, that):
    this_mtime = os.stat(this).st_mtime
    that_mtime = os.stat(that).st_mtime
    return this_mtime > that_mtime


def make_mapping(master_dir, mp3_dir):
    mapping = {master_dir: mp3_dir}
    for master_subdir, dirnames, filenames in os.walk(master_dir):
        mp3_subdir = mapping[master_subdir]
        for master_name in chain(dirnames, filenames):
            mp3_name = clean_filename(master_name)
            master_joined = os.path.join(master_subdir, master_name)
            mp3_joined = os.path.join(mp3_subdir, mp3_name)
            mapping[master_joined] = mp3_joined
    return mapping


def convert_or_link(mapping, redo_tags=False):
    genre_mapping = get_id3v2_genres()

    for master_name, mp3_name in sorted(mapping.items()):

        do_print = lambda x: print('{} {!r}'.format(x, mp3_name))

        if not os.path.exists(master_name):
            # ignore dangling links in master
            pass

        elif os.path.isdir(master_name):
            if not os.path.isdir(mp3_name):
                if os.path.lexists(mp3_name):
                    do_print('unlink')
                    os.unlink(mp3_name)
                do_print('mkdir')
                os.mkdir(mp3_name)

        elif master_name.endswith('.flac'):
            converted = False
            if (not os.path.exists(mp3_name) or
                is_newer_than(master_name, mp3_name)):
                do_print('convert')
                convert_to_mp3(master_name, mp3_name)
                converted = True
            if converted or redo_tags:
                do_print('tags')
                copy_tags(master_name, mp3_name, genre_mapping)

        elif not os.path.exists(mp3_name) or not os.path.samefile(master_name, mp3_name):
            if os.path.lexists(mp3_name):
                if os.path.isdir(mp3_name):
                    do_print('rmtree')
                    shutil.rmtree(mp3_name)
                else:
                    do_print('unlink')
                    os.unlink(mp3_name)

            do_print('symlink')
            symlink_to_mp3(master_name, mp3_name)


def unlink_unmapped(mp3_dir, mapping):
    proper_mp3 = set(mapping.values())
    actual_mp3 = []

    for mp3_subdir, dirnames, filenames in os.walk(mp3_dir):
        actual_mp3.extend(os.path.join(mp3_subdir, name)
            for name in chain(dirnames, filenames))

    for mp3_name in reversed(actual_mp3):
        if mp3_name not in proper_mp3:
            do_print = lambda x: print('{} {!r}'.format(x, mp3_name))
            if os.path.isdir(mp3_name):
                do_print('symlink')
                os.rmdir(mp3_name)
            else:
                do_print('unlink')
                os.unlink(mp3_name)


def get_id3v2_genres():
    mapping = {}
    p1 = Popen(['id3v2', '-L'], stdin=DEVNULL, stdout=PIPE)
    for line in p1.stdout:
        line = line.decode('utf8').strip().lower()
        num, name = line.split(': ', 1)
        mapping.setdefault(name, num)
    return mapping


def get_flac_tags(master_name):
    flac_tags = {}
    p1 = Popen(['metaflac', '--export-tags-to=-', master_name],
        stdin=DEVNULL, stdout=PIPE)
    for line in p1.stdout:
        line = line.decode('utf8').strip()
        if '=' in line:
            name, value = line.split('=', 1)
            flac_tags[name] = value
    return flac_tags


def convert_tags(flac_tags, genre_mapping):
    mp3_tags = dict(flac_tags)

    if 'DATE' in mp3_tags and len(mp3_tags['DATE']) == 4:
        mp3_tags['YEAR'] = mp3_tags['DATE']

    if 'GENRE' in mp3_tags:
        genre_name = mp3_tags['GENRE'].lower()
        genre_num = genre_mapping.get(genre_name)
        if genre_num:
            mp3_tags['GENRE_NUM'] = genre_num

    return mp3_tags


def copy_tags(master_name, mp3_name, genre_mapping):
    assert master_name.endswith('.flac')
    assert mp3_name.endswith('.mp3')

    flac_tags = get_flac_tags(master_name)

    mp3_tags = convert_tags(flac_tags, genre_mapping)

    id3v2_args = []
    for flag, tag in [
        ('-a', 'ARTIST'),
        ('-A', 'ALBUM'),
        ('-t', 'TITLE'),
        ('-T', 'TRACKNUMBER'),
        ('-y', 'YEAR'),
        ('-g', 'GENRE_NUM'),
        ]:
        if tag in mp3_tags:
            id3v2_args.extend([flag, mp3_tags[tag]])

    if id3v2_args:
        subprocess.check_call(['id3v2'] + id3v2_args + [mp3_name])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--redo-tags', action='store_true', default=False)
    parser.add_argument('master', type=str, nargs='?', default='/misc/space/music/master')
    parser.add_argument('mp3', type=str, nargs='?', default='/misc/space/music/mp3')
    args = parser.parse_args()

    mapping = make_mapping(args.master, args.mp3)
    convert_or_link(mapping, redo_tags=args.redo_tags)
    unlink_unmapped(args.mp3, mapping)
    tidy_symlinks(args.mp3)
