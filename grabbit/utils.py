import os
import re

from os.path import join, dirname, basename


def natural_sort(l, field=None):
    '''
    based on snippet found at http://stackoverflow.com/a/4836734/2445984
    '''
    convert = lambda text: int(text) if text.isdigit() else text.lower()

    def alphanum_key(key):
        if field is not None:
            key = getattr(key, field)
        return [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def splitext(path):
    """splitext for paths with directories that may contain dots.
    From https://stackoverflow.com/questions/5930036/separating-file-extensions-using-python-os-path-module"""
    li = []
    path_without_extensions = join(dirname(path), basename(path).split(os.extsep)[0])
    extensions = basename(path).split(os.extsep)[1:]
    li.append(path_without_extensions)
    # li.append(extensions) if you want extensions in another list inside the list that is returned.
    li.extend(extensions)
    return li


def listify(obj):
    ''' Wraps all non-list or tuple objects in a list; provides a simple way
    to accept flexible arguments. '''
    return obj if isinstance(obj, (list, tuple, type(None))) else [obj]
