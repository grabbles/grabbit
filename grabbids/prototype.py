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
        """
        Represents a single file.
        """
        self.name = filename
        self.entities = {}


class Entity(object):

    def __init__(self, name, pattern):
        """
        Represents a single entity defined in the JSON specification.
        Args:
            name (str): The name of the entity (e.g., 'subject', 'run', etc.)
            pattern (str): A regex pattern used to match against file names.
                Must define at least one group, and only the first group is
                kept as the match.
        """
        self.name = name
        self.pattern = pattern
        self.files = {}
        self.regex = re.compile(pattern)

    def matches(self, f):
        """
        Run a regex search against the passed file and update the entity/file
        mappings.
        Args:
            f (File): The File instance to match against.
        """
        m = self.regex.search(f.name)
        if m is not None:
            val = m.group(1)
            f.entities[self.name] = val
            self.files[f.name] = val


class Structure(object):

    def __init__(self, specification, path):
        """
        A container for all the files and metadata found at the specified path.
        Args:
            specification (str): The path to the JSON specification file
                that defines the entities and paths for the current structure.
            path (str): The root path of the structure.
        """
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


    def get(self, entities, return_type='file', filter=None, extensions=None):
        """
        Retrieve files and/or metadata from the current Structure.
        Args:
            entities (str, iterable): One or more entities to retrieve data
                for. Only files that match at least one of the passed entity
                names will be returned.
            return_type (str): What to return. At present, only 'file' works.
            filter (dict): A dictionary of optional key/values to filter the
                entities on. Keys are entity names, values are regexes to
                filter on. For example, passing filter={ 'subject': 'sub-[12]'}
                would return only files that match the first two subjects.
            extensions (str, list): One or more file extensions to filter on.
                Files with any other extensions will be excluded.
        Returns:
            A nested dictionary, with the levels of the hierarchy defined
            in a json spec file (currently using the "result" key).
        """
        if isinstance(entities, string_types):
            entities = [entities]

        result = tree()

        entity_order = self.spec['result']

        if extensions is not None:
            extensions = '(' + '|'.join(extensions) + ')$'


        for filename, file in self.files.items():
            entity_keys = []

            include = True
            _call = 'result'
            for i, ent in enumerate(entity_order):
                key = file.entities.get(ent, "%s-1" % ent)
                _call += '["%s"]' % key

                # Filter on entity values
                if filter is not None and ent in filter:
                    if re.search(filter[ent], key) is None:
                        include = False
                        break

                # Filter on extensions
                if extensions is not None:
                    if re.search(extensions, filename) is None:
                        include = False
                        break


            if include:
                _call += ' = "%s"' % (filename)
                exec(_call)

        return to_dict(result)
