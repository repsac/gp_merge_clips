import os
import shutil
import argparse
import tempfile
from subprocess import Popen

_VERBOSE = True
VALID = ('mp4', 'mov', 'avi')
EXE = 'ffmpeg -f concat -safe 0 -i %(text)s -c:v copy %(output)s'


def merge_clips(path, dryrun=False):
    mapping = _map_clips(path)

    for key in mapping:
        clips = mapping[key]['clips']
        if len(clips) < 2:
            continue

        clips.sort()
        mapping[key].update(_merge_clips(clips, dryrun))
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


def _merge_clips(clips, dryrun):
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
    output = tempfile.mktemp(suffix=ext)
    command = EXE % {
        'text': tmp_text,
        'output': output
    }

    _print("Running: %s" % command)
    if not dryrun:
        proc = Popen(command, shell=True)
        proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("Failed to process '%s'" % command)
        os.remove(tmp_text)
    return {'output': output, 'command': command}


def _map_clips(path):
    nodes = os.listdir(path)

    mtime_mapping = {}
    for node in nodes:
        ext = os.path.splitext(node)[-1]
        if ext[1:].lower() not in VALID:
            continue

        full_path = os.path.join(path, node)
        mtime_mapping[os.stat(full_path).st_mtime] = node

    mtime = [*mtime_mapping.keys()]
    mtime.sort()

    previous_index = None
    sorted_files = [[]]
    for index, mt in enumerate(mtime):
        node = mtime_mapping[mt]
        name = os.path.splitext(node)[0]
        current_index = int(name[1:])

        if current_index - 1 == previous_index:
            sorted_files.append([node])
        else:
            sorted_files[-1].append(node)

        previous_index = current_index

    mapping = {}
    for each in sorted_files:
        if len(each) == 1:
            continue
        name = os.path.splitext(each[0])[0]
        key = str(int(name[1:]))[1:]
        mapping.setdefault(key,
                           {'clips': [os.path.join(path, x) for x in each],
                            'command': None,
                            'output': None})
    return mapping


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default=os.getcwd())
    parser.add_argument('-n', '--dryrun', action='store_true')
    args = parser.parse_args()
    merge_clips(args.path, dryrun=args.dryrun)


if __name__ == '__main__':
    _main()
