import json
import os
import re
from collections import defaultdict, OrderedDict, namedtuple
from six import string_types
from os.path import join, exists, basename, dirname, relpath
import os
import itertools

__all__ = ['File', 'Entity', 'Layout']


class File(object):

    def __init__(self, filename):
        """
        Represents a single file.
        """
        # if not exists(filename):
        #     raise OSError("File '%s' can't be found." % filename)
        self.path = filename
        self.filename = basename(self.path)
        self.dirname = dirname(self.path)
        self.entities = {}

    def matches(self, entities=None, extensions=None):
        if extensions is not None:
            if isinstance(extensions, string_types):
                extensions = [extensions]
            extensions = '(' + '|'.join(extensions) + ')$'
            if re.search(extensions, self.path) is None:
                return False
        if entities is not None:
            for name, val in entities.items():
                if name not in self.entities or \
                    re.search(str(val), self.entities[name]) is None:
                    return False
        return True

    def as_named_tuple(self):
        _File = namedtuple('File', 'filename ' + ' '.join(self.entities.keys()))
        return _File(filename=self.path, **self.entities)


class Entity(object):

    def __init__(self, name, pattern, mandatory=False, missing_value=None,
                 directory=None, inherit=None, **kwargs):
        """
        Represents a single entity defined in the JSON specification.
        Args:
            name (str): The name of the entity (e.g., 'subject', 'run', etc.)
            pattern (str): A regex pattern used to match against file names.
                Must define at least one group, and only the first group is
                kept as the match.
            mandatory (bool): If True, every File _must_ match this entity.
            missing_value (str): Value to use in cases where a placeholder is
                inserted into a hierarchy (e.g., the user wants a hierarchy
                like subject => session => run, but there's only one session).
                If missing_value is None, the name of the entity will be used.
            inherit (list): Specification of the inheritance pattern.
            kwargs (dict): Additional keyword arguments.
        """
        self.name = name
        self.pattern = pattern
        self.mandatory = mandatory
        if missing_value is None:
            missing_value = self.name
        self.missing_value = missing_value
        self.directory = directory
        self.inherit = inherit
        self.files = {}
        self.regex = re.compile(pattern)

    def __iter__(self):
        for i in self.unique():
            yield(i)

    def matches(self, f):
        """
        Run a regex search against the passed file and update the entity/file
        mappings.
        Args:
            f (File): The File instance to match against.
        """
        m = self.regex.search(f.path)
        if m is not None:
            val = m.group(1)
            f.entities[self.name] = val

    def add_file(self, filename, value):
        """ Adds the specified filename to tracking. """
        self.files[filename] = value

    def unique(self):
        return list(set(self.files.values()))

    def count(self, files=False):
        return len(self.files) if files else len(self.unique())


class Layout(object):

    def __init__(self, specification, path):
        """
        A container for all the files and metadata found at the specified path.
        Args:
            specification (str): The path to the JSON specification file
                that defines the entities and paths for the current layout.
            path (str): The root path of the layout.
        """
        self.config = json.load(open(specification, 'r'))
        self.path = path
        self.entities = OrderedDict()
        self.files = {}
        self.mandatory = set()
        self.root = self.config['root']

        # Set up the entities we need to track
        for e in self.config['entities']:
            ent = Entity(**e)
            if ent.mandatory:
                self.mandatory.add(ent)
            self.entities[ent.name] = ent

        # Loop over all files
        for root, directories, filenames in os.walk(path):
            for f in filenames:
                f = File(join(root, f))
                for e in self.entities.values():
                    e.matches(f)
                fe = f.entities.keys()
                # Only keep Files that match at least one Entity, and all
                # mandatory Entities
                if fe and not (self.mandatory - set(fe)):
                    self.files[f.path] = f
                    # Bind the File to all of the matching entities
                    for ent, val in f.entities.items():
                        self.entities[ent].add_file(f.path, val)

    def get(self, filters=None, extensions=None, return_type='file',
            target=None, **kwargs):
        """
        Retrieve files and/or metadata from the current Layout.
        Args:
            return_type (str): What to return. At present, only 'file' works.
            filters (dict): A dictionary of optional key/values to filter the
                entities on. Keys are entity names, values are regexes to
                filter on. For example, passing filter={ 'subject': 'sub-[12]'}
                would return only files that match the first two subjects.
            extensions (str, list): One or more file extensions to filter on.
                Files with any other extensions will be excluded.
            return_type (str): Type of result to return. Valid values:
                'file': returns a list of namedtuples containing file name as
                    well as attribute/value pairs for all named entities.
                'dir': returns a list of directories.
                'id': returns a list of unique IDs. Must be used together with
                    a valid target.
            target (str): The name of the target entity to get results for
                (if return_type is 'dir' or 'id').

        Returns:
            A nested dictionary, with the levels of the hierarchy defined
            in a json spec file (currently using the "result" key).
        """
        result = []
        if filters is None:
            filters = {}
        filters.update(kwargs)
        for filename, file in self.files.items():
            if not file.matches(filters, extensions):
                continue
            result.append(file.as_named_tuple())

        if return_type == 'file':
            return result
        else:
            if target is None:
                raise ValueError('If return_type is "id" or "dir", a valid '
                                 'target entity must also be specified.')
            result = [x for x in result if hasattr(x, target)]
            result = list(set([getattr(x, target) for x in result]))
            if return_type == 'id':
                return result
            elif return_type == 'dir':
                template = self.entities[target].directory
                if template is None:
                    raise ValueError('Return type set to directory, but no '
                                     'directory template is defined for the '
                                     'target entity (%s).')
                return [template.replace('{%s}' % target, x) for x in result]
            else:
                raise ValueError("Invalid return_type specified (must be one "
                                 "of 'file', 'id', or 'dir'.")

    def find(self, target, start=None):

        # Try to take the easy way out
        if start is not None:
            _target = start.split('.')[0] + '.' + target
            if exists(_target):
                return target

        if target in self.entities.keys():
            candidates = list(self.entities[target].files.keys())
        else:
            candidates = []
            for root, directories, filenames in os.walk(path):
                for f in filenames:
                    if re.search(target + '$', f):
                        candidates.append(f)

        if start is None:
            return candidates

        # Walk up the file hierarchy from start, find first match
        if not exists(start):
            raise OSError("The file '%s' doesn't exist." % start)
        elif not start.startswith(self.root):
            raise ValueError("The file '%s' is not contained within the "
                             "current project directory (%s)." % (start, self.root))
        rel = relpath(dirname(start), self.root)
        sep = os.path.sep
        chunks = rel.split(sep)
        n_chunks = len(chunks)
        for i in range(n_chunks, -1, -1):
            path = join(self.root, *chunks[:i])
            patt =  path + '\%s[^\%s]+$' % (sep, sep)
            matches = [x for x in candidates if re.search(patt, x)]
            if matches:
                if len(matches) == 1:
                    return matches[0]
                else:
                    raise ValueError("Ambiguous target: more than one candidate "
                                     "file found in directory '%s'." % path)
        return None

    def unique(self, entity):
        """
        Return a list of unique values for the named entity.
        Args:
            entity (str): The name of the entity to retrieve unique values of.
        """
        return self.entities[entity].unique()

    def count(self, entity, files=False):
        """
        Return the count of unique values or files for the named entity.
        Args:
            entity (str): The name of the entity.
            files (bool): If True, counts the number of filenames that contain
                at least one value of the entity, rather than the number of
                unique values of the entity.
        """
        return self.entities[entity].count(files)
