import os
import shutil
import tempfile
from pathlib import Path
from random import randint
import gp_merge_clips


def _cleanup(path):
    shutil.rmtree(path)


def _create_test_files(tmpdir):
    base_index = randint(1, 99999)
    for each in range(6):
        if each % 2:
            end_range = randint(5, 11)
        else:
            end_range = 1
        str_index = str(base_index)
        unique_index = str_index[1:]
        gindex = int(str_index[0])
        for index in range(end_range):
            str_index = '{}{}'.format(gindex + index, unique_index)
            name = 'G{:>07d}.{}'.format(
                int(str_index), gp_merge_clips.VALID[0].upper())
            Path(os.path.join(tmpdir, name)).touch()
        base_index = int(str_index)
        base_index += 1


def _test_results(results):
    print(results)
    assert len(results) == 3, "Incorrect number of collecions"
    print("Test 1 passed.")
    for index, key in enumerate(results):
        for each in results[key]['clips']:
            split = os.path.splitext(each)[0]
            assert split.endswith(key), "Invalid file in sequence"
        print("Test {} passed.".format(index+2))
    print("All tests have passed!")


def _main():
    tmpdir = tempfile.mkdtemp()
    try:
        _create_test_files(tmpdir)
        results = gp_merge_clips.merge_clips(tmpdir, dryrun=True)
        _test_results(results)
    except Exception:
        _cleanup(tmpdir)
        raise

    _cleanup(tmpdir)


if __name__ == '__main__':
    _main()
