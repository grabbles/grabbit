from __future__ import print_function, division, absolute_import
from json_minify import json_minify
import os.path as osp



def remove_comments(filename, strip_space=False):
    """
    Remove // and /* */ comments from template file 
    (.cjson for commented jason by convention)
    Create a json file where filename is
    """
    assert osp.isfile(filename)
    string_to_minify = ''.join(open(filename).readlines())

    fnbase = osp.splitext(osp.basename(filename))[0] 
    #fnext = osp.splitext(osp.basename(filename))[1]
    nocomment_filename = osp.join(osp.dirname(filename), fnbase, '_nc.json') 

    str_nc = json_minify(string_to_minify, strip_space=strip_space)
    
    try:
        with open(nocomment_filename, "w") as fout:
            fout.write(str_nc)
    except:
        IOError, "could not write {}".format(str_nc)

    return  nocomment_filename
    


# fn = './test_template.cjson'
# import numpy as np
# with fh as open(fn):
#     print fh.read()
# fh = open(fn)
# fh.readlines()
# s = open(fn).readlines()
# minify.json_minify(s)
# s
# s[3]
# s.join()
# ''.join(s)
# minify.json_minify(''.join(s))
# minify.json_minify(''.join(s), strip_space=False)
# fn
# import os.path as osp
# osp.basename(fn)
# osp.splitext(osp.basename(fn))
# osp.splitext(osp.basename(fn))[0]
# fnbase = osp.splitext(osp.basename(fn))[0]
# fntuple = osp.splitext(osp.basename(fn))[1]
