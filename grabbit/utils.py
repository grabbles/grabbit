import re

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