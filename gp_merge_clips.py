import os
import shutil
import argparse
import tempfile
from subprocess import Popen

VALID = ('mp4', 'mov', 'avi')
EXE = 'ffmpeg -f concat -safe 0 -i %(text)s -c:v copy %(output)s'


def merge_clips(path, dryrun=False):
    mapping = _map_clips(path)

    for key in mapping:
        clips = mapping[key]
        if len(clips) < 2:
            continue

        clips.sort()
        merged = _merge_clips(clips, dryrun)
        key_path = os.path.join(path, key)
        if not os.path.exists(key_path):
            if dryrun:
                print("DRYRUN: creating '%s'" % key_path)
            else:
                os.makedirs(key_path)

        for clip in clips:
            _move(clip, key_path, dryrun)

        _move(merged, clips[0], dryrun)


def _move(src, dst, dryun):
    if dryun:
        print("Moving %s > %s" % (src, dst))
    else:
        shutil.move(src, dst)


def _merge_clips(clips, dryrun):
    text = []
    for clip in clips:
        text.append("file '%s'" % clip)
    text = '\n'.join(text)

    tmp_text = tempfile.mktemp()
    if dryrun:
        print("Writing:\n%s\n>>%s" % (text, tmp_text))
    else:
        with open(tmp_text, 'w') as open_file:
            open_file.write(text)

    ext = os.path.splitext(clips[0])[-1]
    output = tempfile.mktemp(suffix=ext)
    command = EXE % {
        'text': tmp_text,
        'output': output
    }

    print("Running: %s" % command)
    if not dryrun:
        proc = Popen(command, shell=True)
        proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("Failed to process '%s'" % command)
        os.remove(tmp_text)
    return output


def _map_clips(path):
    mapping = {}
    for each in os.listdir(path):
        full_path = os.path.join(path, each)
        if not os.path.isfile(full_path):
            continue

        name, ext = os.path.splitext(each)
        if ext[1:].lower() not in VALID:
            continue

        key = name[4:]
        mapping.setdefault(key, [])
        mapping[key].append(full_path)
    return mapping


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default=os.getcwd())
    parser.add_argument('-n', '--dryrun', action='store_true')
    args = parser.parse_args()
    merge_clips(args.path, dryrun=args.dryrun)


if __name__ == '__main__':
    _main()
