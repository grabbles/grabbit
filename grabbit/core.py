import json
import os
import re
from collections import defaultdict, OrderedDict, namedtuple
from grabbit.external import six, inflect
from grabbit.utils import natural_sort, listify
from grabbit.extensions.writable import build_path, write_contents_to_file
from os.path import (join, basename, dirname, abspath, split, isabs, exists)
from functools import partial
from copy import deepcopy
import warnings


__all__ = ['File', 'Entity', 'Layout']


class File(object):

    def __init__(self, filename):
        """
        Represents a single file.
        """
        self.path = filename
        self.filename = basename(self.path)
        self.dirname = dirname(self.path)
        self.tags = {}

    @property
    def entities(self):
        return {k: v.value for k, v in self.tags.items()}

    @property
    def domains(self):
        return tuple(set([t.entity.domain.name for t in self.tags.values()]))

    def _matches(self, entities=None, extensions=None, domains=None,
                 regex_search=False):
        """
        Checks whether the file matches all of the passed entities and
        extensions.

        Args:
            entities (dict): A dictionary of entity names -> regex patterns.
            extensions (str, list): One or more file extensions to allow.
            domains (str, list): One or more domains the file must match.
            regex_search (bool): Whether to require exact match (False) or
                regex search (True) when comparing the query string to each
                entity.
        Returns:
            True if _all_ entities and extensions match; False otherwise.
        """
        if extensions is not None:
            if isinstance(extensions, six.string_types):
                extensions = [extensions]
            extensions = '(' + '|'.join(extensions) + ')$'
            if re.search(extensions, self.path) is None:
                return False

        if domains is not None:
            domains = listify(domains)
            if not set(self.domains) & set(domains):
                return False

        if entities is not None:

            for name, val in entities.items():

                if name not in self.tags:
                    return False

                def make_patt(x):
                    patt = '%s' % x
                    if isinstance(x, (int, float)):
                        # allow for leading zeros if a number was specified
                        # regardless of regex_search
                        patt = '0*' + patt
                    if not regex_search:
                        patt = '^%s$' % patt
                    return patt

                ent_patts = [make_patt(x) for x in listify(val)]
                patt = '|'.join(ent_patts)

                if re.search(patt, str(self.tags[name].value)) is None:
                    return False
        return True

    def as_named_tuple(self):
        """
        Returns the File as a named tuple. The full path plus all entity
        key/value pairs are returned as attributes.
        """
        entities = self.entities
        _File = namedtuple('File', 'filename ' + ' '.join(entities.keys()))
        return _File(filename=self.path, **entities)

    def copy(self, path_patterns, symbolic_link=False, root=None,
             conflicts='fail'):
        ''' Copy the contents of a file to a new location, with target
        filename defined by the current File's entities and the specified
        path_patterns. '''
        new_filename = build_path(self.entities, path_patterns)
        if not new_filename:
            return None

        if new_filename[-1] == os.sep:
            new_filename += self.filename

        if symbolic_link:
            contents = None
            link_to = self.path
        else:
            with open(self.path, 'r') as f:
                contents = f.read()
            link_to = None

        write_contents_to_file(new_filename, contents=contents,
                               link_to=link_to, content_mode='text', root=root,
                               conflicts=conflicts)


class Domain(object):

    def __init__(self, name, config, root):
        """
        A set of rules that applies to one or more directories
        within a Layout.

        Args:
            name (str): The name of the Domain.
            config (dict): The configuration dictionary that defines the
                entities and paths for the current domain.
            root (str, list): The root directory or directories to which the
                Domain's rules applies. Can be either a single path, or a list.
        """

        self.name = name
        self.config = config
        self.root = root
        self.entities = {}
        self.files = []
        self.path_patterns = []

        self.include = listify(self.config.get('include', []))
        self.exclude = listify(self.config.get('exclude', []))

        if self.include and self.exclude:
            raise ValueError("The 'include' and 'exclude' arguments cannot "
                             "both be set. Please pass at most one of these "
                             "for domain '%s'." % self.name)

        if 'default_path_patterns' in config:
            self.path_patterns += listify(config['default_path_patterns'])

    def add_entity(self, ent):
        ''' Add an Entity.

        Args:
            ent (Entity): The Entity to add.
        '''
        self.entities[ent.name] = ent

    def add_file(self, file):
        ''' Add a file to tracking.

        Args:
            file (File): The File to add to tracking.
        '''
        self.files.append(file)


Tag = namedtuple('Tag', ['entity', 'value'])


class Entity(object):

    def __init__(self, name, pattern=None, domain=None, mandatory=False,
                 directory=None, map_func=None, dtype=None, **kwargs):
        """
        Represents a single entity defined in the JSON config.

        Args:
            name (str): The name of the entity (e.g., 'subject', 'run', etc.)
            pattern (str): A regex pattern used to match against file names.
                Must define at least one group, and only the first group is
                kept as the match.
            mandatory (bool): If True, every File _must_ match this entity.
            directory (str): Optional pattern defining a directory associated
                with the entity.
            map_func (callable): Optional callable used to extract the Entity's
                value from the passed string (instead of trying to match on the
                defined .pattern).
            domain (Domain): The Domain the Entity belongs to.
            kwargs (dict): Additional keyword arguments.
            dtype (str): The optional data type of the Entity values. Must be
                one of 'int', 'float', 'bool', or 'str'. If None, no type
                enforcement will be attempted, which means the dtype of the
                value may be unpredictable.
        """
        if pattern is None and map_func is None:
            raise ValueError("Invalid specification for Entity '%s'; no "
                             "pattern or mapping function provided. Either the"
                             " 'pattern' or the 'map_func' arguments must be "
                             "set." % name)
        self.name = name
        self.pattern = pattern
        self.domain = domain
        self.mandatory = mandatory
        self.directory = directory
        self.map_func = map_func
        self.kwargs = kwargs

        if isinstance(dtype, six.string_types):
            dtype = eval(dtype)
        if dtype not in [str, float, int, bool, None]:
            raise ValueError("Invalid dtype '%s'. Must be one of int, float, "
                             "bool, or str." % dtype)
        self.dtype = dtype

        self.files = {}
        self.regex = re.compile(pattern) if pattern is not None else None
        self.id = '.'.join([getattr(domain, 'name', ''), name])

    def __iter__(self):
        for i in self.unique():
            yield(i)

    def __deepcopy__(self, memo):

        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result

        for k, v in self.__dict__.items():
            new_val = getattr(self, k) if k == 'regex' else deepcopy(v, memo)
            setattr(result, k, new_val)
        return result

    def matches(self, f, update_file=False):
        """
        Determine whether the passed file matches the Entity and update the
        Entity/File mappings.

        Args:
            f (File): The File instance to match against.
            update_file (bool): If True, the file's tag list is updated to
                include the current Entity.
        """
        if self.map_func is not None:
            val = self.map_func(f)
        else:
            m = self.regex.search(f.path)
            val = m.group(1) if m is not None else None

        if val is None:
            return False

        if update_file:
            if self.dtype is not None:
                val = self.dtype(val)
            f.tags[self.name] = Tag(self, val)

        return True

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


class LayoutMetaclass(type):
    ''' Metaclass for Layout; used to enable merging of multiple Layouts into
    a single Layout when a list of paths is passed as input.
    '''
    def __call__(cls, path, *args, **kwargs):

        paths = listify(path)
        if len(paths) == 1:
            return super(LayoutMetaclass, cls).__call__(paths[0], *args,
                                                        **kwargs)
        layouts = []
        for p in paths:
            layout = super(LayoutMetaclass, cls).__call__(p, *args, **kwargs)
            layouts.append(layout)
        return merge_layouts(layouts)


class Layout(six.with_metaclass(LayoutMetaclass, object)):

    def __init__(self, path, config=None, index=None, dynamic_getters=False,
                 absolute_paths=True, regex_search=False, entity_mapper=None,
                 path_patterns=None, config_filename='layout.json',
                 include=None, exclude=None):
        """
        A container for all the files and metadata found at the specified path.

        Args:
            path (str): The root path of the layout.
            config (str, list, dict): A specification of the configuration
                file(s) defining domains to use in the Layout. Must be one of:

                - A dictionary containing config information
                - A string giving the path to a JSON file containing the config
                - A list, where each element is one of the above

            index (str): Optional path to a saved index file. If a valid value
                is passed, this index is used to populate Files and Entities,
                and the normal indexing process (which requires scanning all
                files in the project) is skipped.
            dynamic_getters (bool): If True, a get_{entity_name}() method will
                be dynamically added to the Layout every time a new Entity is
                created. This is implemented by creating a partial function of
                the get() function that sets the target argument to the
                entity name.
            absolute_paths (bool): If True, grabbit uses absolute file paths
                everywhere (including when returning query results). If False,
                the input path will determine the behavior (i.e., relative if
                a relative path was passed, absolute if an absolute path was
                passed).
            regex_search (bool): Whether to require exact matching (True)
                or regex search (False, default) when comparing the query
                string to each entity in .get() calls. This sets a default for
                the instance, but can be overridden in individual .get()
                requests.
            entity_mapper (object, str): An optional object containing methods
                for indexing specific entities. If passed, the object must
                contain a named method for every value that appears in the
                JSON config file under the "mapper" key of an Entity's entry.
                For example, if an entity "type" is defined that contains the
                key/value pair "mapper": "extract_type", then the passed object
                must contain an .extract_type() method.
                    Alternatively, the special string "self" can be passed, in
                which case the current Layout instance will be used as the
                entity mapper (implying that the user has subclassed Layout).
            path_patterns (str, list): One or more filename patterns to use
                as a default path pattern for this layout's files.  Can also
                be specified in the config file.
            config_filename (str): The name of directory-specific config files.
                Every directory will be scanned for this file, and if found,
                the config file will be read in and added to the list of
                configs.
            include (str, list): A string or list specifying regexes used to
                globally filter files when indexing. A file or directory
                *must* match at least of the passed values in order to be
                retained in the index. Cannot be used together with 'exclude'.
            exclude (str, list): A string or list specifying regexes used to
                globally filter files when indexing. If a file or directory
                *must* matches any of the passed values, it will be dropped
                from indexing. Cannot be used together with 'include'.
        """

        if include is not None and exclude is not None:
            raise ValueError("You cannot specify both the include and exclude"
                             " arguments. Please pass at most one of these.")

        self.root = abspath(path) if absolute_paths else path
        self.entities = OrderedDict()
        self.files = {}
        self.mandatory = set()
        self.dynamic_getters = dynamic_getters
        self.regex_search = regex_search
        self.entity_mapper = self if entity_mapper == 'self' else entity_mapper
        self.path_patterns = path_patterns if path_patterns else []
        self.config_filename = config_filename
        self.domains = OrderedDict()
        self.include = listify(include or [])
        self.exclude = listify(exclude or [])

        if config is not None:
            for c in listify(config):
                self._load_domain(c)

        if index is None:
            self.index()
        else:
            self.load_index(index)

    def _load_domain(self, config, root=None):

        if isinstance(config, six.string_types):
            config = json.load(open(config, 'r'))

        if 'name' not in config:
            raise ValueError("Config file missing 'name' attribute.")
        if config['name'] in self.domains:
            raise ValueError("Config with name '%s' already exists in "
                             "Layout. Name of each config file must be "
                             "unique across entire Layout.")
        if root is not None:
            config['root'] = root

        if 'root' not in config:
            warnings.warn("No valid root directory found for domain '%s'."
                          " Falling back on the Layout's root directory. "
                          "If this isn't the intended behavior, make sure "
                          "the config file for this domain includes a "
                          "'root' key." % config['name'])
            config['root'] = self.root
        elif config['root'] == '.':
            config['root'] = self.root
        elif not isabs(config['root']):
            _root = config['root']
            config['root'] = join(self.root, config['root'])
            if not exists(config['root']):
                msg = ("Relative path '%s' for domain '%s' interpreted as '%s'"
                       ", but this directory doesn't exist. Either specify the"
                       " domain root as an absolute path, or make sure it "
                       "points to a valid directory when appended to the "
                       "Layout's root (%s)." % (_root, config['name'],
                                                config['root'], self.root))
                raise ValueError(msg)

        # Load entities
        domain = Domain(config['name'], config, config['root'])
        for e in config.get('entities', []):
            self.add_entity(domain=domain, **e)

        self.domains[domain.name] = domain

    def get_domain_entities(self, domains=None, file=None):
        # Get all Entities included in the specified Domains, in the same
        # order as Domains in the list. Alternatively, if a file is passed,
        # identify its domains and then return the entities.

        if file is None:
            if domains is None:
                domains = list(self.domains.keys())
        else:
            domains = self._get_domains_for_file(file)

        ents = {}
        for d in domains:
            ents.update(self.domains[d].entities)
        return ents

    def _check_inclusions(self, f, domains=None):
        ''' Check file or directory against regexes in config to determine if
            it should be included in the index '''

        filename = f if isinstance(f, six.string_types) else f.path

        if os.path.isabs(filename) and filename.startswith(
                self.root + os.path.sep):
            # for filenames under the root - analyze relative path to avoid
            # bringing injustice to the grandkids of some unfortunately named
            # root directories.
            filename = os.path.relpath(filename, self.root)

        if domains is None:
            domains = list(self.domains.keys())

        domains = [self.domains[dom] for dom in domains]

        # Inject the Layout at the first position for global include/exclude
        domains.insert(0, self)
        for dom in domains:
            # If file matches any include regex, then True
            if dom.include:
                for regex in dom.include:
                    if re.match(regex, filename):
                        return True
                return False
            else:
                # If file matches any exclude regex, then False
                for regex in dom.exclude:
                    if re.match(regex, filename, flags=re.UNICODE):
                        return False

        return True

    def _validate_dir(self, d):
        ''' Extend this in subclasses to provide additional directory
        validation. Will be called the first time a directory is read in; if
        False is returned, the directory will be ignored and dropped from the
        layout.
        '''
        return self._validate_file(d)

    def _validate_file(self, f):
        ''' Extend this in subclasses to provide additional file validation.
        Will be called the first time each file is read in; if False is
        returned, the file will be ignored and dropped from the layout. '''
        return True

    def _get_files(self):
        ''' Returns all files in project (pre-filtering). Extend this in
        subclasses as needed. '''
        return os.walk(self.root, topdown=True)

    def _make_file_object(self, root, f):
        ''' Initialize a new File oject from a directory and filename. Extend
        in subclasses as needed. '''
        return File(join(root, f))

    def _reset_index(self):
        # Reset indexes
        self.files = {}
        for ent in self.entities.values():
            ent.files = {}

    def _get_domains_for_file(self, f):
        if isinstance(f, File):
            return f.domains
        domains = []
        for d in self.domains.values():
            for path in listify(d.root):
                if f.startswith(path):
                    domains.append(d.name)
                    break
        return domains

    def _index_file(self, root, f, domains=None, update_layout=True):

        # If domains aren't explicitly passed, figure out what applies
        if domains is None:
            domains = self._get_domains_for_file(root)

        # Create the file object--allows for subclassing
        f = self._make_file_object(root, f)

        if not (self._check_inclusions(f) and self._validate_file(f)):
            return

        for d in domains:
            self.domains[d].add_file(f)

        entities = self.get_domain_entities(domains)

        if entities:
            self.files[f.path] = f

        for e in entities.values():
            e.matches(f, update_file=True)

        file_ents = f.tags.keys()

        # Only keep Files that match at least one Entity, and all
        # mandatory Entities
        if update_layout and file_ents and not (self.mandatory -
                                                set(file_ents)):
            self.files[f.path] = f
            # Bind the File to all of the matching entities
            for name, tag in f.tags.items():
                ent_id = tag.entity.id
                self.entities[ent_id].add_file(f.path, tag.value)

        return f

    def _find_entity(self, entity):
        ''' Find an Entity instance by name. Checks both name and id fields.'''
        if entity in self.entities:
            return self.entities[entity]
        _ent = [e for e in self.entities.values() if e.name == entity]
        if len(_ent) > 1:
            raise ValueError("Entity name '%s' matches %d entities. To "
                             "avoid ambiguity, please prefix the entity "
                             "name with its domain (e.g., 'bids.%s'." %
                             (entity, len(_ent), entity))
        if _ent:
            return _ent[0]

        raise ValueError("No entity '%s' found." % entity)

    def index(self):

        self._reset_index()

        dataset = self._get_files()

        # Loop over all files
        for root, directories, filenames in dataset:

            # Determine which Domains apply to the current directory
            domains = self._get_domains_for_file(root)

            # Exclude directories that match exclude regex from further search
            full_dirs = [os.path.join(root, d) for d in directories]

            def check_incl(directory):
                return self._check_inclusions(directory, domains)

            full_dirs = filter(check_incl, full_dirs)
            full_dirs = filter(self._validate_dir, full_dirs)
            directories[:] = [split(d)[1] for d in full_dirs]

            if self.config_filename in filenames:
                config_path = os.path.join(root, self.config_filename)
                config = json.load(open(config_path, 'r'))
                root = config.get('root', root)
                self._load_domain(config, root=root)

                # Filter Domains if current dir's config file has an
                # include directive
                if 'domains' in config:
                    missing = set(config['domains']) - set(domains)
                    if missing:
                        msg = ("Missing configs '%s' specified in include "
                               "directive of config '%s'. Please make sure "
                               "these config files are accessible from the "
                               "directory %s.") % (missing, config['name'],
                                                   root)
                        raise ValueError(msg)
                    domains = config['domains']
                domains.append(config['name'])

                filenames.remove(self.config_filename)

            for f in filenames:
                self._index_file(root, f, domains)

    def save_index(self, filename):
        ''' Save the current Layout's index to a .json file.

        Args:
            filename (str): Filename to write to.

        Note: At the moment, this won't serialize directory-specific config
        files. This means reconstructed indexes will only work properly in
        cases where there aren't multiple layout specs within a project.
        '''
        data = {}
        for f in self.files.values():
            entities = {v.entity.id: v.value for k, v in f.tags.items()}
            data[f.path] = entities
        with open(filename, 'w') as outfile:
            json.dump(data, outfile)

    def load_index(self, filename, reindex=False):
        ''' Load the Layout's index from a plaintext file.

        Args:
            filename (str): Path to the plaintext index file.
            reindex (bool): If True, discards entity values provided in the
                loaded index and instead re-indexes every file in the loaded
                index against the entities defined in the config. Default is
                False, in which case it is assumed that all entity definitions
                in the loaded index are correct and do not need any further
                validation.

        Note: At the moment, directory-specific config files aren't serialized.
        This means reconstructed indexes will only work properly in cases
        where there aren't multiple layout specs within a project.
        '''
        self._reset_index()
        data = json.load(open(filename, 'r'))

        for path, ents in data.items():

            # If file path isn't absolute, assume it's relative to layout root
            if not isabs(path):
                path = join(self.root, path)

            root, f = dirname(path), basename(path)
            if reindex:
                self._index_file(root, f)
            else:
                f = self._make_file_object(root, f)
                tags = {k: Tag(self.entities[k], v) for k, v in ents.items()}
                f.tags = tags
                self.files[f.path] = f

                for ent, val in f.entities.items():
                    self.entities[ent].add_file(f.path, val)

    def add_entity(self, domain, **kwargs):
        ''' Add a new Entity to tracking. '''

        # Set the entity's mapping func if one was specified
        map_func = kwargs.get('map_func', None)
        if map_func is not None and not callable(kwargs['map_func']):
            if self.entity_mapper is None:
                raise ValueError("Mapping function '%s' specified for Entity "
                                 "'%s', but no entity mapper was passed when "
                                 "initializing the current Layout. Please make"
                                 " sure the 'entity_mapper' argument is set." %
                                 (map_func, kwargs['name']))
            map_func = getattr(self.entity_mapper, kwargs['map_func'])
            kwargs['map_func'] = map_func

        ent = Entity(domain=domain, **kwargs)
        domain.add_entity(ent)

        if ent.mandatory:
            self.mandatory.add(ent.id)
        if ent.directory is not None:
            ent.directory = ent.directory.replace('{{root}}', self.root)
        self.entities[ent.id] = ent
        if self.dynamic_getters:
            func = partial(getattr(self, 'get'), target=ent.name,
                           return_type='id')
            func_name = inflect.engine().plural(ent.name)
            setattr(self, 'get_%s' % func_name, func)

    def get(self, return_type='tuple', target=None, extensions=None,
            domains=None, regex_search=None, **kwargs):
        """
        Retrieve files and/or metadata from the current Layout.

        Args:
            return_type (str): Type of result to return. Valid values:
                'tuple': returns a list of namedtuples containing file name as
                    well as attribute/value pairs for all named entities.
                'file': returns a list of matching filenames.
                'dir': returns a list of directories.
                'id': returns a list of unique IDs. Must be used together with
                    a valid target.
                'obj': returns a list of matching File objects.
            target (str): The name of the target entity to get results for
                (if return_type is 'dir' or 'id').
            extensions (str, list): One or more file extensions to filter on.
                Files with any other extensions will be excluded.
            domains (list): Optional list of domain names to scan for files.
                If None, all available domains are scanned.
            regex_search (bool or None): Whether to require exact matching
                (False) or regex search (True) when comparing the query string
                to each entity. If None (default), uses the value found in
                self.
            kwargs (dict): Any optional key/values to filter the entities on.
                Keys are entity names, values are regexes to filter on. For
                example, passing filter={ 'subject': 'sub-[12]'} would return
                only files that match the first two subjects.

        Returns:
            A named tuple (default) or a list (see return_type for details).
        """
        if regex_search is None:
            regex_search = self.regex_search

        result = []
        filters = {}
        filters.update(kwargs)
        for filename, file in self.files.items():
            if not file._matches(filters, extensions, domains, regex_search):
                continue
            result.append(file)

        if return_type == 'file':
            return natural_sort([f.path for f in result])

        if return_type == 'tuple':
            result = [r.as_named_tuple() for r in result]
            return natural_sort(result, field='filename')

        if return_type.startswith('obj'):
            return result

        else:
            valid_entities = self.get_domain_entities(domains)

            if target is None:
                raise ValueError('If return_type is "id" or "dir", a valid '
                                 'target entity must also be specified.')
            result = [x for x in result if target in x.entities]

            if return_type == 'id':
                result = list(set([x.entities[target] for x in result]))
                return natural_sort(result)

            elif return_type == 'dir':
                template = valid_entities[target].directory
                if template is None:
                    raise ValueError('Return type set to directory, but no '
                                     'directory template is defined for the '
                                     'target entity (\"%s\").' % target)
                # Construct regex search pattern from target directory template
                to_rep = re.findall('\{(.*?)\}', template)
                for ent in to_rep:
                    patt = valid_entities[ent].pattern
                    template = template.replace('{%s}' % ent, patt)
                template += '[^\%s]*$' % os.path.sep
                matches = [f.dirname for f in self.files.values()
                           if re.search(template, f.dirname)]
                return natural_sort(list(set(matches)))

            else:
                raise ValueError("Invalid return_type specified (must be one "
                                 "of 'tuple', 'file', 'id', or 'dir'.")

    def unique(self, entity):
        """
        Return a list of unique values for the named entity.

        Args:
            entity (str): The name of the entity to retrieve unique values of.
        """
        return self._find_entity(entity).unique()

    def count(self, entity, files=False):
        """
        Return the count of unique values or files for the named entity.

        Args:
            entity (str): The name of the entity.
            files (bool): If True, counts the number of filenames that contain
                at least one value of the entity, rather than the number of
                unique values of the entity.
        """
        return self._find_entity(entity).count(files)

    def as_data_frame(self, **kwargs):
        """
        Return information for all Files tracked in the Layout as a pandas
        DataFrame.

        Args:
            kwargs: Optional keyword arguments passed on to get(). This allows
                one to easily select only a subset of files for export.
        Returns:
            A pandas DataFrame, where each row is a file, and each column is
                a tracked entity. NaNs are injected whenever a file has no
                value for a given attribute.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("What are you doing trying to export a Layout "
                              "as a pandas DataFrame when you don't have "
                              "pandas installed? Eh? Eh?")
        if kwargs:
            files = self.get(return_type='obj', **kwargs)
        else:
            files = self.files.values()
        data = pd.DataFrame.from_records([f.entities for f in files])
        data.insert(0, 'path', [f.path for f in files])
        return data

    def get_nearest(self, path, return_type='file', strict=True, all_=False,
                    ignore_strict_entities=None, **kwargs):
        ''' Walk up the file tree from the specified path and return the
        nearest matching file(s).

        Args:
            path (str): The file to search from.
            return_type (str): What to return; must be one of 'file' (default)
                or 'tuple'.
            strict (bool): When True, all entities present in both the input
                path and the target file(s) must match perfectly. When False,
                files will be ordered by the number of matching entities, and
                partial matches will be allowed.
            all_ (bool): When True, returns all matching files. When False
                (default), only returns the first match.
            ignore_strict_entities (list): Optional list of entities to
                exclude from strict matching when strict is True. This allows
                one to search, e.g., for files of a different type while
                matching all other entities perfectly by passing
                ignore_strict_entities=['type'].
            kwargs: Optional keywords to pass on to .get().
        '''

        entities = {}
        for ent in self.entities.values():
            m = ent.regex.search(path)
            if m:
                entities[ent.name] = m.group(1)

        # Remove any entities we want to ignore when strict matching is on
        if strict and ignore_strict_entities is not None:
            for k in ignore_strict_entities:
                entities.pop(k, None)

        results = self.get(return_type='file', **kwargs)

        folders = defaultdict(list)

        for filename in results:
            f = self.files[filename]
            folders[f.dirname].append(f)

        def count_matches(f):
            f_ents = f.entities
            keys = set(entities.keys()) & set(f_ents.keys())
            shared = len(keys)
            return [shared, sum([entities[k] == f_ents[k] for k in keys])]

        matches = []

        while True:
            if path in folders and folders[path]:

                # Sort by number of matching entities. Also store number of
                # common entities, for filtering when strict=True.
                num_ents = [[f] + count_matches(f) for f in folders[path]]
                # Filter out imperfect matches (i.e., where number of common
                # entities does not equal number of matching entities).
                if strict:
                    num_ents = [f for f in num_ents if f[1] == f[2]]
                num_ents.sort(key=lambda x: x[2], reverse=True)

                if num_ents:
                    matches.append(num_ents[0][0])

                if not all_:
                    break
            try:
                _path, _ = split(path)
                if _path == path:
                    break
                path = _path
            except Exception:
                break

        matches = [m.path if return_type == 'file' else m.as_named_tuple()
                   for m in matches]
        return matches if all_ else matches[0] if matches else None

    def clone(self):
        return deepcopy(self)

    def parse_file_entities(self, filename, domains=None):
        root, f = dirname(filename), basename(filename)
        if not root and domains is None:
            raise ValueError("If a relative path is provided as the filename "
                             "argument, you *must* specify the names of the "
                             "domains whose entities are to be extracted. "
                             "Available domains for the current layout are: %s"
                             % list(self.domains.keys()))
        result = self._index_file(root, f, domains, update_layout=False)
        return result.entities

    def build_path(self, source, path_patterns=None, strict=False):
        ''' Constructs a target filename for a file or dictionary of entities.

        Args:
            source (str, File, dict): The source data to use to construct the
                new file path. Must be one of:
                - A File object
                - A string giving the path of a File contained within the
                  current Layout.
                - A dict of entities, with entity names in keys and values in
                  values
            path_patterns (list): Optional path patterns to use to construct
                the new file path. If None, the Layout-defined patterns will
                be used.
            strict (bool): If True, all entities must be matched inside a
                pattern in order to be a valid match. If False, extra entities
                will be ignored so long as all mandatory entities are found.
        '''
        if isinstance(source, six.string_types):
            source = self.files[source]

        if isinstance(source, File):
            source = source.entities

        if path_patterns is None:
            path_patterns = self.path_patterns

        return build_path(source, path_patterns, strict)

    def copy_files(self, files=None, path_patterns=None, symbolic_links=True,
                   root=None, conflicts='fail', **get_selectors):
        """
        Copies one or more Files to new locations defined by each File's
        entities and the specified path_patterns.

        Args:
            files (list): Optional list of File objects to write out. If none
                provided, use files from running a get() query using remaining
                **kwargs.
            path_patterns (str, list): Write patterns to pass to each file's
                write_file method.
            symbolic_links (bool): Whether to copy each file as a symbolic link
                or a deep copy.
            root (str): Optional root directory that all patterns are relative
                to. Defaults to current working directory.
            conflicts (str): One of 'fail', 'skip', 'overwrite', or 'append'
                that defines the desired action when a output path already
                exists. 'fail' raises an exception; 'skip' does nothing;
                'overwrite' overwrites the existing file; 'append' adds a
                suffix
                to each file copy, starting with 0. Default is 'fail'.
            **get_selectors (kwargs): Optional key word arguments to pass into
                a get() query.
        """
        _files = self.get(return_type='objects', **get_selectors)
        if files:
            _files = list(set(files).intersection(_files))

        for f in _files:
            f.copy(path_patterns, symbolic_link=symbolic_links,
                   root=root, conflicts=conflicts)

    def write_contents_to_file(self, entities, path_patterns=None,
                               contents=None, link_to=None,
                               content_mode='text', conflicts='fail',
                               strict=False, domains=None):
        """
        Write arbitrary data to a file defined by the passed entities and
        path patterns.

        Args:
            entities (dict): A dictionary of entities, with Entity names in
                keys and values for the desired file in values.
            path_patterns (list): Optional path patterns to use when building
                the filename. If None, the Layout-defined patterns will be
                used.
            contents (object): Contents to write to the generate file path.
                Can be any object serializable as text or binary data (as
                defined in the content_mode argument).
            conflicts (str): One of 'fail', 'skip', 'overwrite', or 'append'
            that defines the desired action when the output path already
            exists. 'fail' raises an exception; 'skip' does nothing;
            'overwrite' overwrites the existing file; 'append' adds a suffix
            to each file copy, starting with 1. Default is 'fail'.
            strict (bool): If True, all entities must be matched inside a
                pattern in order to be a valid match. If False, extra entities
                will be ignored so long as all mandatory entities are found.
            domains (list): List of Domains to scan for path_patterns. Order
                determines precedence (i.e., earlier Domains will be scanned
                first). If None, all available domains are included.

        """
        if not path_patterns:
            path_patterns = self.path_patterns
            if domains is None:
                domains = list(self.domains.keys())
            for dom in domains:
                path_patterns.extend(self.domains[dom].path_patterns)
        path = build_path(entities, path_patterns, strict)
        write_contents_to_file(path, contents=contents, link_to=link_to,
                               content_mode=content_mode, conflicts=conflicts,
                               root=self.root)
        self._index_file(self.root, path)


def merge_layouts(layouts):
    ''' Utility function for merging multiple layouts.

    Args:
        layouts (list): A list of BIDSLayout instances to merge.
    Returns:
        A BIDSLayout containing merged files and entities.
    Notes:
        Layouts will be merged in the order of the elements in the list. I.e.,
        the first Layout will be updated with all values in the 2nd Layout,
        then the result will be updated with values from the 3rd Layout, etc.
        This means that order matters: in the event of entity or filename
        conflicts, later layouts will take precedence.
    '''
    layout = layouts[0].clone()

    for l in layouts[1:]:
        layout.files.update(l.files)
        layout.domains.update(l.domains)

        for k, v in l.entities.items():
            if k not in layout.entities:
                layout.entities[k] = v
            else:
                layout.entities[k].files.update(v.files)

    return layout
