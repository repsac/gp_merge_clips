# gp_merge_clips
GoPro splits long recordings out to multiple files. This library is for locating movies (from a GoPro memory card) in a directory
and determining which movies belong to a sequence and merging them into a single movie file.

Command line usage:
```shell

# execute on a specified directory (destination defaults to $PWD)
> python -m gp_merge_clips <path to root folder>
```