"""
GoPro splits long recordings out to multiple files (chapters).
This library is for locating movies (from a GoPro memory card)
in a directory and determining which movies belong to a sequence
and merging them into a single movie file.

>>> import gp_merge_clips
>>> gp_merge_clips.merge_clips('/path/to/root/dir')

Command line
$ python -m gp_merge_clips /path/to/root/dir
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


def merge_clips(path, dryrun=False):
    """
    Locate movie clips that are chapters of one recording
    and merge them to single movie file(s).

    :param path: root path to a directory containing the movie files
    :rtype: {}
    :returns: {
        <clip basename>: {
            'clips': [<manifest of clips to be merged>, ...]
            'command': <ffmpeg command that is generated>
            'output': <merged movie file>
        }
    }
    """
    mapping = _map_chapters(path)
    
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
    """
    :param str message:
    """
    global _VERBOSE
    if _VERBOSE:
        print(message)


def _move(src, dst, dryun):
    """
    :param str src:
    :param str dst:
    :param bool dryrun:
    """
    if dryun:
        _print("Moving %s > %s" % (src, dst))
    else:
        shutil.move(src, dst)


def _merge_clips(clips, dryrun):
    """
    ffmpeg plays nicely when the files that are to be concatenated
    are written to a text file, and the file is passed to ffmpeg

    the new file is written to temp

    :param [] clips: list of movie clips to be concatenated
    :param bool dryrun:
    :returns: {
        'output': <concatenated file>
        'command': <ffmpeg command executed>
    }
    """
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


def _sort_by_mtime(path, movies):
    """
    Sort movies by the mtime, this gives us a list of movies that is not
    sorted by name. This will help distinguish clips that are chapters
    of a single shot

    :param str path: root path
    :param [] movies: movie file names
    :rtype: [<str>, <str>, ...]
    """
    mtime_mapping = {}
    for movie in movies:
        full_path = os.path.join(path, movie)
        mtime_mapping[os.stat(full_path).st_mtime] = movie

    mtime = [*mtime_mapping.keys()]
    mtime.sort()
    return [mtime_mapping[x] for x in mtime]    


def _map_movies(movies):
    """
    In order to sequentially sort the movie clips we have to strip
    the 'GH' prefix and extension and cast the rest of the filename
    to an integer

    input:
    ['GH010013.MP4', 'GH020013.MP4', 'GH030013.MP4']

    output:
    {10013: 'GH010013.MP4', 20013: 'GH020013.MP4', 30013: 'GH030013.MP4'}

    :param [] movies:
    :rtype: {}
    """
    mapped_movies = {}
    for movie in movies:
        basename = os.path.splitext(movie)[0]
        mapped_movies[int(basename[2:])] = movie
    return mapped_movies


def _sort_sequential_movies(movies):
    """
    The logic here will figure out the sequentially named files and
    return the correct sequences

    A list that looks like this:
    ['GH010013.MP4', 'GH010014.MP4', 'GH010015.MP4', 'GH010016.MP4', 
     'GH010017.MP4', 'GH010018.MP4', 'GH020013.MP4', 'GH020016.MP4',
     'GH030013.MP4', 'GH030016.MP4', 'GH040016.MP4']

    Should be sorted like this
    [['GH010013.MP4', 'GH010014.MP4', 'GH010015.MP4', 'GH010016.MP4', 
      'GH010017.MP4', 'GH010018.MP4'], 
     ['GH020013.MP4'],
     ['GH020016.MP4'],
     ['GH030013.MP4'],
     ['GH030016.MP4'],
     ['GH040016.MP4']]

    The nested list that has the smallest number should be the list
    containing all movies that are first chapter or solo (un-chaptered).
    This is the list that should be returned
    ['GH010013.MP4', 'GH010014.MP4', 'GH010015.MP4', 'GH010016.MP4', 
      'GH010017.MP4', 'GH010018.MP4']

    :param [] movies: movie movies
    :rtype: []
    """
    mapped_movies = _map_movies(movies)
    keys = [*mapped_movies]
    keys.sort()
    sequential_movies = []

    for gb in groupby(enumerate(keys), lambda ix : ix[0] - ix[1]):
        grouped = list(map(itemgetter(1), gb[1]))
        sequential_movies.append([mapped_movies[x] for x in grouped])
    sorted(sequential_movies, key=lambda x: x[0])

    try:
        first_chapters = sequential_movies[0]
    except IndexError:
        first_chapters = []

    return first_chapters


def _map_chapters(path):
    """
    Create a mapping table (dict) that associates chapters

    :param str path:
    :rtype: {}
    :returns: {
        <clip basename>: {
            'clips': [<manifest of clips to be merged>, ...]
            'command': <ffmpeg command that is generated>
            'output': <merged movie file>
        }
    }
    """
    movies = []
    mapping = {}

    # locate all valid media files
    for movie in os.listdir(path):
        ext = os.path.splitext(movie)[-1]
        if ext[1:].lower() in VALID:
            movies.append(movie)

    # isolate sequential files, that should also be the first
    # chapter of a single shot
    sequential_movies = _sort_sequential_movies(movies)
    if not sequential_movies:
        return mapping

    # get movies sorted by their mtime (ignore sequential naming)
    sorted_by_mtime = _sort_by_mtime(path, movies)

    # here we create a diff of indices that will identify the 
    # the sorted_by_mtime would look something like this
    # ['GH010013.MP4', 'GH020013.MP4', 'GH030013.MP4', 'GH010014.MP4',
    #  'GH010015.MP4', 'GH010016.MP4', 'GH020016.MP4', 'GH030016.MP4',
    #  'GH040016.MP4', 'GH010017.MP4', 'GH010018.MP4']

    # the sequential nodes would look like this
    # ['GH010013.MP4', 'GH010014.MP4', 'GH010015.MP4', 'GH010016.MP4',
    #  'GH010017.MP4', 'GH010018.MP4']

    # the diff would isolate the indices of the movies (first example)
    # that are missing from the second example.
    # [1, 2, 6, 7, 8]

    diff_movies = list(set(sorted_by_mtime) - set(sequential_movies))
    diff_indices = [sorted_by_mtime.index(d) for d in diff_movies]
    diff_indices.sort()

    # now we group the indices to look like this
    # [[1, 2], [6, 7, 8]]

    # pulling the first and last index of each nested list we know the
    # index range of the chapters that belong to one shot
    for gb in groupby(enumerate(diff_indices), lambda ix : ix[0] - ix[1]):
        grouped_indices = list(map(itemgetter(1), gb[1]))
        grouped_movies = sorted_by_mtime[grouped_indices[0]-1:
                                         grouped_indices[-1]+1]
        key = os.path.splitext(grouped_movies[0])[0]
        mapping.setdefault(key,
                           {'clips': [os.path.join(path, x)
                                      for x in grouped_movies],
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