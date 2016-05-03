from __future__ import print_function, division, absolute_import
from json_minify import json_minify
import json
import os.path as osp


def get_tmp_json_fn(filename):
    """
    give back a tmporary json filename based on input filename
    """
    fnbase = osp.splitext(osp.basename(filename))[0] 
    #fnext = osp.splitext(osp.basename(fnbase))[1]
    nocomment_filename = osp.join(osp.dirname(filename), '_'+ fnbase +'_nc.json') 

    return nocomment_filename


def remove_comments(filename, strip_space=False, writejsonfile=True, no_cmmt_fn='', overwrite=True):
    """
    Remove // and /* */ comments from template file. By convention
    the file with comments will be a *.cjson (commented json). 

    Create a *.json file without comments. Appart from the comments, 
    the function will also join two lines that if the last character
    of the first line is a '\'. 

    parameters:
    -----------
    filename: string
        a filename jason like with comments
    strip_space: bool
        if True strip space ' ', '\n', '\r'
    overwrite: bool
        if file without comments exist, can we overwrite?

    returns:
    --------
    dict: 
        the dictionnary with the json object 

    """

    # assert osp.isfile(filename)
    list_to_minify = open(filename).readlines()
    string_to_minify = ''.join(remove_multiline_sep(list_to_minify))

    str_no_cmmt = json_minify(string_to_minify, strip_space=strip_space)


    if writejsonfile:
        if no_cmmt_fn == '':
            no_cmmt_fn = get_tmp_json_fn(filename)

        # check that there is no previous no_cmmt_fn or that we can overwrite
        assert not osp.isfile(no_cmmt_fn) or overwrite

        try:
            with open(no_cmmt_fn, "w") as fout:
                fout.write(str_no_cmmt)
        except:
            IOError, "could not write {}".format(str_no_cmmt)
   
    try:
        dsdic = json.load(str_no_cmmt)
        print(dsdic)
        return dsdic
    except:
        ValueError, "could not json-load {}".format(str_no_cmmt)

    #return  dsdic


def remove_multiline_sep(liststr):
    """
    from a list of lines, remove the '\' at the end of a line and join with next line
    after removing the white spaces ' \t' of the next line.
    
    parameters:
    -----------
    liststr: list of strings
        typically the output of a readlines

    returns
    --------
    list of strings
    """

    to_rm_secondline = ' \t'
    if not liststr:
        raise Exception, "Nothing in this list {}".format(liststr)

    if len(liststr) == 1: 
        # last character a \
        if len(liststr[0]) > 2 and liststr[0][-2] == '\\': 
            return [liststr[0][:-2]]
        else:
            return liststr
    else:
        # two or more in the list, first and second are str, rest is list
        first, second, rest = liststr[0], liststr[1], liststr[2:]

        if len(first) > 2 and first[-2] == '\\':
            # rm the '\', then rm white spaces in second
            return remove_multiline_sep([first[:-2] + \
                                         second.strip(to_rm_secondline)] + rest)
        else:
            return [first] + remove_multiline_sep([second] + rest) 


class DataLayout(object):

    def __init__(self, layout_filename):
        assert osp.isfile(layout_filename), "{} not a file".format(layout_filename)
        self.jsonfile = layout_filename
        remove_comments

    def ds_get(self):
        """
    
        """
        pass

