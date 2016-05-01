from __future__ import print_function, true_division
import minify
import os.path as osp





def remove_comments(filename, strip_space=strip_space):
    """
    Remove // and /* */ comments from template file 
    (.cjson for commented jason by convention)
    """
    assert osp.isfilename(filename)
    string_to_minify = ''.join(open(fn).readlines())

    fnbase = osp.splitext(osp.basename(filename))[0] 
    #fnext = osp.splitext(osp.basename(filename))[1]
    nocomment_filename = osp.join(osp.dirname(filename), fnbase, '_nc.json') 

    str_nc = minify.json_minify(string_to_minify, strip_space=False)
    
    try:
        with open(nocomment_filename, "w") as fout:
            fout.write(str_nc)
    except:
        ValueError, print("could not write {}", str_nc)

    return
    


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
