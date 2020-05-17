"""
GoPro splits long recordings out to multiple files. This library is
for locating movies (from a GoPro memory card) in a directory
and determining which movies belong to a sequence and merging them
into a single movie file.

> import gp_merge_clips
> gp_merge_clips.merge_clips('/path/to/root/dir')
"""
import os
import shutil
import argparse
import tempfile
from itertools import groupby
from operator import itemgetter
from subprocess import Popen

_VERBOSE = True
VALID = ('mp4', 'mov', 'avi')
EXE = 'ffmpeg -f concat -safe 0 -i %(text)s -c:v copy %(output)s'


def merge_clips(path, output_dir=None, dryrun=False):
    """
    Locate movie clips associated with sequences and merge them to single movie file(s).

    :param path: root path to a directory containing the movie files
    :param output_dir: optional output directory for merged movie files
    :rtype: {}
    :returns: {
        <clip basename>: {
            'clips': [<manifest of clips to be merged>, ...]
            'command': <ffmpeg command that is generated>
            'output': <merged movie file>
        }
    }
    """
    mapping = _map_clips(path)
    output_dir = output_dir or path

    for key in mapping:
        clips = mapping[key]['clips']
        if len(clips) < 2:
            continue

        clips.sort()
        mapping[key].update(_merge_clips(clips, output_dir, dryrun))
        key_path = os.path.join(path, key)
        if not os.path.exists(key_path):
            if dryrun:
                _print("DRYRUN: creating '%s'" % key_path)
            else:
                os.makedirs(key_path)

        for clip in clips:
            _move(clip, key_path, dryrun)

        _move(mapping[key]['output'], clips[0], dryrun)

    return mapping


def _print(message):
    global _VERBOSE
    if _VERBOSE:
        print(message)


def _move(src, dst, dryun):
    if dryun:
        _print("Moving %s > %s" % (src, dst))
    else:
        shutil.move(src, dst)


def _merge_clips(clips, output_dir, dryrun):
    text = []
    for clip in clips:
        text.append("file '%s'" % clip)
    text = '\n'.join(text)

    tmp_text = tempfile.mktemp()
    if dryrun:
        _print("Writing:\n%s\n>>%s" % (text, tmp_text))
    else:
        with open(tmp_text, 'w') as open_file:
            open_file.write(text)

    ext = os.path.splitext(clips[0])[-1]
    tmp_output = tempfile.mktemp(suffix=ext)
    command = EXE % {
        'text': tmp_text,
        'output': tmp_output
    }

    _print("Running: %s" % command)
    output = os.path.join(output_dir, 
                          "MERGED_{}".format(os.path.basename(clips[0])))
    if not dryrun:
        proc = Popen(command, shell=True)
        proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("Failed to process '%s'" % command)
        os.remove(tmp_text)
        shutil.move(tmp_output, output)
    return {'output': output, 'command': command}


def _sort_by_mtime(path, nodes):
    mtime_mapping = {}
    for node in nodes:
        full_path = os.path.join(path, node)
        mtime_mapping[os.stat(full_path).st_mtime] = node

    mtime = [*mtime_mapping.keys()]
    mtime.sort()
    return [mtime_mapping[x] for x in mtime]    


def _map_nodes(nodes):
    mapped_nodes = {}
    for node in nodes:
        basename = os.path.splitext(node)[0]
        mapped_nodes[int(basename[2:])] = node
    return mapped_nodes


def _sort_sequential_nodes(nodes):
    mapped_nodes = _map_nodes(nodes)
    keys = [*mapped_nodes]
    keys.sort()
    sequential_nodes = [[]]
    for gb in groupby(enumerate(keys), lambda ix : ix[0] - ix[1]):
        grouped = list(map(itemgetter(1), gb[1]))
        sequential_nodes.append([mapped_nodes[x] for x in grouped])
    sequential_nodes.sort(key=len, reverse=True)
    return sequential_nodes[0]


def _map_clips(path):
    nodes = []
    mapping = {}
    for node in os.listdir(path):
        ext = os.path.splitext(node)[-1]
        if ext[1:].lower() in VALID:
            nodes.append(node)

    sequential_nodes = _sort_sequential_nodes(nodes)
    if len(sequential_nodes) <= 1:
        return mapping

    sorted_by_mtime = _sort_by_mtime(path, nodes)
    diff_nodes = list(set(sorted_by_mtime) - set(sequential_nodes))
    diff_indices = [sorted_by_mtime.index(d) for d in diff_nodes]
    diff_indices.sort()
    for gb in groupby(enumerate(diff_indices), lambda ix : ix[0] - ix[1]):
        grouped_indices = list(map(itemgetter(1), gb[1]))
        grouped_nodes = sorted_by_mtime[grouped_indices[0]-1:grouped_indices[-1]+1]
        key = os.path.splitext(grouped_nodes[0])[0]
        mapping.setdefault(key,
                           {'clips': [os.path.join(path, x) for x in grouped_nodes],
                            'command': None,
                            'output': None})
    return mapping


def _intersection(str1, str2):
    res = ''
    for i in str1: 
        if i in str2 and not i in res: 
            res += i
    return res


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default=os.getcwd())
    parser.add_argument('-n', '--dryrun', action='store_true')
    args = parser.parse_args()
    merge_clips(args.path, dryrun=args.dryrun)


if __name__ == '__main__':
    _main()
