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

    def _matches(self, entities=None, extensions=None):
        """
        Checks whether the file matches all of the passed entities and
        extensions.
        Args:
            entities (dict): A dictionary of entity names -> regex
                patterns.
            extensions (str, list): One or more file extensions to allow.
        Returns:
            True if _all_ entities and extensions match; False otherwise.
        """
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
        """
        Returns the File as a named tuple. The full path plus all entity
        key/value pairs are returned as attributes.
        """
        _File = namedtuple('File', 'filename ' + ' '.join(self.entities.keys()))
        return _File(filename=self.path, **self.entities)


class Entity(object):

    def __init__(self, name, pattern, mandatory=False, missing_value=None,
                 directory=None, inherit=None, **kwargs):
        """
        Represents a single entity defined in the JSON config.
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
            inherit (list): specification of the inheritance pattern.
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
        """ Returns all unique values/levels for the current entity. """
        return list(set(self.files.values()))

    def count(self, files=False):
        """ Returns a count of unique values or files.
        Args:
            files (bool): When True, counts all files mapped to the Entity.
                When False, counts all unique values.
        Returns: an int.
        """
        return len(self.files) if files else len(self.unique())


class Layout(object):

    def __init__(self, path, config=None):
        """
        A container for all the files and metadata found at the specified path.
        Args:
            config (str): The path to the JSON config file
                that defines the entities and paths for the current layout.
            path (str): The root path of the layout.
        """

        self.root = path
        self.entities = OrderedDict()
        self.files = {}
        self.mandatory = set()

        if config is not None:
            self._load_config(config)

    def _load_config(self, config):
        if isinstance(config, string_types):
            config = json.load(open(config, 'r'))

        for e in config['entities']:
            self.add_entity(**e)

        self.index()

    def index(self):

        # Reset indexes
        self.files = {}
        for ent in self.entities.values():
            ent.files = {}

        # Loop over all files
        for root, directories, filenames in os.walk(self.root):
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

    def add_entity(self, **kwargs):
                # Set up the entities we need to track
            ent = Entity(**kwargs)
            if ent.mandatory:
                self.mandatory.add(ent.name)
            if ent.directory is not None:
                ent.directory = ent.directory.replace('{{root}}', self.root)
            self.entities[ent.name] = ent

    def get(self, extensions=None, return_type='file',
            target=None, **kwargs):
        """
        Retrieve files and/or metadata from the current Layout.
        Args:
            return_type (str): What to return. At present, only 'file' works.
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
            kwargs (dict): Any optional key/values to filter theentities on.
                Keys are entity names, values are regexes to filter on. For
                example, passing filter={ 'subject': 'sub-[12]'} would return
                only files that match the first two subjects.

        Returns:
            A named tuple (default) or a list (see return_type for details).
        """
        result = []
        filters = {}
        filters.update(kwargs)
        for filename, file in self.files.items():
            if not file._matches(filters, extensions):
                continue
            result.append(file.as_named_tuple())

        if return_type == 'file':
            return result
        else:
            if target is None:
                raise ValueError('If return_type is "id" or "dir", a valid '
                                 'target entity must also be specified.')
            result = [x for x in result if hasattr(x, target)]

            if return_type == 'id':
                return list(set([getattr(x, target) for x in result]))
            elif return_type == 'dir':
                template = self.entities[target].directory
                if template is None:
                    raise ValueError('Return type set to directory, but no '
                                     'directory template is defined for the '
                                     'target entity (\"%s\").' % target)
                # Inject entity IDs
                to_rep = re.findall('\{(.*?)\}', template)
                for i, file in enumerate(result):
                    dir_ = template
                    for ent in to_rep:
                        dir_ = dir_.replace('{%s}' % ent, getattr(file, ent))
                    result[i] = dir_
                return list(set(result))
            else:
                raise ValueError("Invalid return_type specified (must be one "
                                 "of 'file', 'id', or 'dir'.")

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


