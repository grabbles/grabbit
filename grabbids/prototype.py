import json
from glob import glob
import os
import re
from collections import defaultdict
from six import string_types
from pprint import pprint
from os.path import dirname, join

def get_test_data_path():
    return join(dirname(__file__), 'tests')

# Utils for creating trees and converting them to plain dicts 
def tree(): return defaultdict(tree)
def to_dict(t):
    if not isinstance(t, dict):
        return t
    return {k: to_dict(t[k]) for k in t }

class File(object):

    def __init__(self, filename):
        self.name = filename
        self.entities = {}


class Entity(object):

    def __init__(self, name, pattern):
        self.name = name
        self.pattern = pattern
        self.files = {}
        self.regex = re.compile(pattern)

    def matches(self, f):
        m = self.regex.search(f.name)
        if m is not None:
            val = m.group(1)
            f.entities[self.name] = val
            self.files[f.name] = val


class Structure(object):

    def __init__(self, specification, path):

        self.spec = json.load(open(specification, 'r'))
        self.path = path
        self.entities = {}
        self.files = {}

        # Set up the entities we need to track
        for e in self.spec['entities']:
            name, pattern = e['name'], e['pattern']
            self.entities[name] = Entity(name, pattern)

        # Loop over all files
        for root, directories, filenames in os.walk(path):
            for f in filenames:
                f = File(f)
                for e in self.entities.values():
                    e.matches(f)
                if f.entities:
                    self.files[f.name] = f


    def get(self, entities, return_type='file', filter=None):
        if isinstance(entities, string_types):
            entities = [entities]

        result = tree()

        entity_order = self.spec['result']

        for fn, file in self.files.items():
            entity_keys = []

            include = True
            _call = 'result'
            for i, ent in enumerate(entity_order):
                key = file.entities.get(ent, "%s-1" % ent)
                _call += '["%s"]' % key

                if filter is not None and ent in filter:
                    if re.search(filter[ent], key) is None:
                        include = False
                        break

            if include:
                _call += ' = "%s"' % (file.name)
                exec(_call)

        return to_dict(result)


if __name__ == "__main__":
    spec_file = join(get_test_data_path(), 'specs', 'test.json')
    bids_dir = join(get_test_data_path(), 'data', 'ds005')
    struct = Structure(spec_file, bids_dir)

    pprint(struct.get('subject', filter={'subject': 'sub-0[1234]'}))

