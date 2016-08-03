import minify
ls
fn = './test_template.cjson'
import numpy as np
np.loadtxt(fn)
with open(fn) as fh:
    print(fh.read())
fh = open(fn)
fh.readlines()
s = open(fn).readlines()
minify.json_minify(s)
s
s[3]
s.join()
''.join(s)
minify.json_minify(''.join(s))
minify.json_minify(''.join(s), strip_space=False)
fn
import os.path as osp
osp.basename(fn)
osp.splitext(osp.basename(fn))
osp.splitext(osp.basename(fn))[0]
fnbase = osp.splitext(osp.basename(fn))
fntuple = osp.splitext(osp.basename(fn))
