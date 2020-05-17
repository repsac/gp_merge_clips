import os
import time
import shutil
import tempfile
from pathlib import Path
from random import randint
import gp_merge_clips

# The first 3 movies on the card are not part of sequence
TEST_FRAMES_1 = (10010, 10011, 10012,
                 10013, 20013, 30013,
                 10014, 10015,
                 10016, 20016, 30016, 40016,
                 10017, 10018)

# The first movies on the card are part of a sequence
TEST_FRAMES_2 = (10013, 20013, 30013,
                 10014, 10015,
                 10016, 20016, 30016, 40016,
                 10017, 10018)

# There are no sequences found
TEST_FRAMES_3 = (10010, 10011, 10012,
                 10013, 10014, 10015)


def _cleanup(path):
    if path is not None:
        shutil.rmtree(path)


def _create_test_files(frames, tmpdir):   
    for frame in frames:
        name = 'GH{:>06d}.{}'.format(frame, gp_merge_clips.VALID[0].upper())
        Path(os.path.join(tmpdir, name)).touch()
        time.sleep(0.1)


def _test_results_1(results):
    "Test 1"
    def test_clip_names(clips, names):
        for i,j in zip(clips, names):
            assert os.path.basename(i) == j, "{} != {}".format(os.path.basename(i), j)

    assert len(results) == 2, "Incorrect number of collections"
    assert 'GH010013' in results, "Missing 'GH010013'"
    assert len(results['GH010013']['clips']) == 3, "Incorrect number of clips for 'GH010013'"
    test_clip_names(results['GH010013']['clips'],
                    ('GH010013.MP4', 'GH020013.MP4', 'GH030013.MP4'))
    test_clip_names(results['GH010016']['clips'],
                    ('GH010016.MP4', 'GH020016.MP4', 'GH030016.MP4', 'GH040016.MP4'))
    assert 'GH010016' in results, "Missing 'GH010016'"
    assert len(results['GH010016']['clips']) == 4, "Incorrect number of clips for 'GH010016'"


def _test_results_2(results):
    "Test 2"
    _test_results_1(results)


def _test_results_3(results):
    "Test 3"
    assert len(results) == 0, "Collections found, there should not be any@"


def _main():
    tmpdir = None
    func = None
    mapping = (
        (TEST_FRAMES_1, _test_results_1),
        (TEST_FRAMES_2, _test_results_2),
        (TEST_FRAMES_3, _test_results_3)
    )
    try:
        for frames, func in mapping:
            tmpdir = tempfile.mkdtemp()
            _create_test_files(frames, tmpdir)
            results = gp_merge_clips.merge_clips(tmpdir, dryrun=True)
            func(results)
            _cleanup(tmpdir)
            print("{} has passed".format(func.__doc__))
    except Exception:
        _cleanup(tmpdir)
        if func is not None:
            print("ERROR: {} has failed".format(func.__doc__))
        raise

    print("All tests have passed")


if __name__ == '__main__':
    _main()