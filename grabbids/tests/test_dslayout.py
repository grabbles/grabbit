from __future__ import division, print_function, absolute_import

import json
import os.path as osp 
import grabbids.dslayout as ds 

# from nose.tools import (assert_true, 
#                         assert_false, 
#                         assert_equal)

TEST_TEMPLATE = '/home/jb/code/grabbids/grabbids/tests/test_template.cjson'
DATA_BASEDIR = '/home/jb/code/grabbids/grabbids/tests/data/ds005/'


def test_remove_comments():
    """
    """
    
    nocomment_json_fname = ds.get_tmp_json_fn(TEST_TEMPLATE)
    assert nocomment_json_fname == '/home/jb/code/grabbids/grabbids/tests/_test_template_nc.json'
    
    dsdic = ds.remove_comments(TEST_TEMPLATE, strip_space=False, 
                                write_json_file=True, no_cmmt_fn='', overwrite=True)

    assert osp.isfile(nocomment_json_fname) 
    try:
        with open(nocomment_json_fname) as fjson:
            __ = json.load(fjson)
            print(__)
    except:
        raise Exception, "{} not json?".format(nocomment_json_fname)

def test_remove_multiline_sep():
    """
    note :      \\ for \, 
                \n for newline
    """
    liststr = ['abc\n', 'a b c d e long line \\\n', '   \t rest of the line']
    expected = ['abc\n', 'a b c d e long line rest of the line']

    listreturned = ds.remove_multiline_sep(liststr)
    for elt1, elt2 in zip(listreturned, expected):
        assert elt1 == elt2, "{} :isnt: {}".format(elt1, elt2)
    
    liststr = ['abc\n']
    expected = ['abc\n']

    listreturned = ds.remove_multiline_sep(liststr)
    for elt1, elt2 in zip(listreturned, expected):
        assert elt1 == elt2, "{} :isnt: {}".format(elt1, elt2)


def test_read_layout():
    """

    """
    template = TEST_TEMPLATE    
    # initialize object layout
    try:
        layout = ds.layout(template)
    except:
        raise Exception, "could not initialize layout with file "\
                                                    .format(template)

    # no base dir given: should be ""
    assert layout.get('base_dir') == ""

    try:
        layout = ds.layout(template, base_dir=DATA_BASEDIR)
    except:
        raise Exception, "could not initialize layout with files "\
                                                    .format(template, DATA_BASEDIR)

# get the list of subject directories:
subject_dirs = layout.get('subjects') # or layout.subjects ?

# get a specific subject directories:

this_sub_dir = layout.subject(sub_value) # works because subject top in hierarchy

# get a specific run directories:

this_run_dir = layout.subject(sub_value).session(None).run(run_value) # 
this_run_dir = layout.run(run_value, sub='*',ses=None) # 

#"images": "{subjects}/func/{subject}_{task}_{run}_bold.nii.gz"
images = layout.get("images", sub='*', task='*', run='02')
# or 
images = layout.images(sub='*', task='*', run='02')



#
#dlayo = lo.get_layout(JSONTEST, dbase = DATABASEDIR)
#
#def test_get_layout():
#
#    assert 'subjects' in dlayo.keys()
#    assert 'sessions' in dlayo.keys()
#    assert 'runs' in dlayo.keys()
#    assert 'run' not in dlayo.keys()
#
#def test_get_key_dict():
#
#    key_dict_expected = {'runs': u'run', 'subjects': u'sub', 'sessions': u'sess'}
#    dstate = lo._get_key_dict(dlayo, entities = ["subjects", "sessions", "runs"])
#    assert dstate == key_dict_expected
#
#def test_get_pth_globFalse():
#    #  get pth with glob = False
#
#    pth, pth_dict = lo._get_pth(dlayo, 'subjects', glob=False)
#    assert pth == DATABASEDIR
#    assert pth_dict == {}
#
#    pth, pth_dict = lo._get_pth(dlayo, 'sessions', glob=False)
#    print("\n",pth)
#    expected_pth =  osp.join(DATABASEDIR, 'sub{sub:02d}')
#    print('expected_pth: ',expected_pth)
#    assert pth == expected_pth
#    assert pth_dict == {u'sub': None}
#
#    pth, pth_dict = lo._get_pth(dlayo, 'runs', glob=False)
#    print("\n",pth)
#    expected_pth = osp.join(DATABASEDIR, 'sub{sub:02d}', 'sess{sess:02d}', 'preproc') 
#    print('expected_pth: ',expected_pth)
#    assert pth == expected_pth
#    assert pth_dict == {u'sess': None, u'sub': None}
#
#
#def test_get_pth_globTrue():
#    #  get pth with glob = True
#
#    pth = lo._get_pth(dlayo, 'subjects', glob=True)
#    assert pth == DATABASEDIR
#
#    pth = lo._get_pth(dlayo, 'sessions', glob=True)
#    print("\n",pth)
#    expected_pth =  osp.join(DATABASEDIR, 'sub*')
#    print('expected_pth: ',expected_pth)
#    assert pth == expected_pth
#
#    pth = lo._get_pth(dlayo, 'runs', glob=True)
#    print("\n",pth)
#    expected_pth = osp.join(DATABASEDIR, 'sub*', 'sess*', 'preproc') 
#    print('expected_pth: ',expected_pth)
#    assert pth == expected_pth
#
#
#def test_get_glb_globFalse():
#    glob=False 
#    verbose=False
#
#    fil, fdict = lo._get_glb(dlayo, 'subjects', glob=glob, verbose=verbose)
#    expected_fil =  'sub*' 
#    print("fil, expected_fil, fdict", fil, expected_fil, fdict)
#    assert_true(fil == expected_fil)
#    assert fdict == {}
#    
#    fil, fdict = lo._get_glb(dlayo, 'sessions', glob=glob, verbose=verbose)
#    expected_fil =  'sess*' 
#    print("fil, expected_fil, fdict", fil, expected_fil, fdict)
#    assert_true(fil == expected_fil)
#    assert fdict == {}
#
#    fil, fdict = lo._get_glb(dlayo, 'smoothed', glob=glob, verbose=verbose)
#    expected_fil =  'srasub{sub:02d}_sess{sess:02d}_run{run:02d}-????.nii*' 
#    print("fil, expected_fil, fdict", fil, expected_fil, fdict)
#    assert_true(fil == expected_fil)
#    assert fdict == {u'sess': None, u'run': None, u'sub': None}
#
#    fil, fdict = lo._get_glb(dlayo, 'wm_mask', glob=glob)
#    expected_fil =  'wm_func_res_final.nii.gz' 
#    print("fil, expected_fil, fdict", fil, expected_fil, fdict)
#    assert_true(fil == expected_fil)
#    assert fdict == {} 
#
#def test_get_glb_globTrue():
#    glob = True 
#    verbose = False
#    fdict = None
#
#    fil = lo._get_glb(dlayo, 'subjects', glob=glob, verbose=verbose)
#    expected_fil =  'sub*' 
#    assert fil == expected_fil
#    
#    fil = lo._get_glb(dlayo, 'sessions', glob=glob, verbose=verbose)
#    expected_fil =  'sess*' 
#    assert fil == expected_fil
#
#    fil = lo._get_glb(dlayo, 'smoothed', glob=glob, verbose=verbose)
#    expected_fil =  'srasub*_sess*_run*-????.nii*' 
#    assert fil == expected_fil
#    assert fdict == None 
#
#    fil = lo._get_glb(dlayo, 'wm_mask', glob=glob)
#    expected_fil =  'wm_func_res_final.nii.gz' 
#    assert fil == expected_fil
#    assert fdict == None 
#
#def test_get_pthglb_globFalse():
#
#    glob =  False
#    verbose = False
#
#    fil, fdict = lo._get_pthglb(dlayo, 'subjects', glob=glob, verbose=verbose)
#    expected_fil =  osp.join(DATABASEDIR, 'sub*')
#    assert fil == expected_fil
#    assert fdict == {}
#
#    fil, fdict = lo._get_pthglb(dlayo, 'sessions', glob=glob, verbose=verbose)
#    expected_fil =  osp.join(DATABASEDIR, 'sub{sub:02d}/sess*') 
#    assert fil == expected_fil
#    assert fdict == {u'sub': None}
#
#def test_get_aunique():
#
#    dstate = {'sess': 2, 'run': 1, 'sub': 1}
#    csf_mask = lo._get_aunique(dlayo, "csf_mask", dstate)
#    expected_csf_mask = osp.join(DATABASEDIR, 
#                        'sub01/sess02/preproc/csf_in_func_res/csf_func_res_final.nii.gz')
#    assert csf_mask == expected_csf_mask
#
#def test_get_alistof():
#
#    dstate = {'sess': 2, 'run': 1, 'sub': 1}
#    aal_files = lo._get_alistof(dlayo, "aal_roi", dstate)
#    expected_len = 116
#    aal_files.sort()
#    expected_first_file = DATABASEDIR + \
#                        u'/sub01/sess02/preproc/coreg/rraal_Amygdala_L__________.nii'   
#    assert expected_len == len(aal_files) 
#    assert aal_files[0] == expected_first_file
#
#    
#
