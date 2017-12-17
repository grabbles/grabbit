import logging
import os
import re
import sys
from grabbit.core import File, Layout
from grabbit.utils import splitext, listify
from os.path import join, dirname, exists, islink, isabs, isdir
from six import string_types

__all__ = ['replace_entities', 'build_path', 'write_contents_to_file',
           'WritableFile', 'WritableLayout']


def replace_entities(pattern, entities):
    """
    Replaces all entity names in the a given pattern with the corresponding
    values provided by entities.

    Args:
        pattern (str): A path pattern that contains entity names denoted
            by curly braces.
            For example: 'sub-{subject}/{{var-{name}}}/{id}.csv'
        entities (dict): A dictionary mapping entity names to entity values.

    Returns:
        A new string with the entity values inserted where entity names
        were denoted in the provided pattern.
    """
    new_path = pattern
    ents = re.findall('\{(.*?)\}', pattern)
    ents_matched = True
    for ent in ents:
        if ent in entities:
            new_path = new_path.replace('{%s}' % ent, str(entities[ent]))
        else:
            # An entity in the pattern is not an entity for this file
            ents_matched = False

    if ents_matched:
        return new_path
    else:
        return None


def build_path(path_patterns, entities):
    """
    Constructs a path given a set of entities and a list of potential
    filename patterns to use.

    Args:
        path_patterns (str, list): One or more filename patterns to write
            the file to. Entities should be represented by the name
            surrounded by curly braces. Optional portions of the patterns
            should be denoted by double curly braces.
            Pattern example: 'sub-{subject}/{{var-{name}}}/{id}.csv'
            Example result: 'sub-01/var-SES/1045.csv'
        entities (dict): A dictionary mapping entity names to entity values.

    Returns:
        A constructed path for this file based on the provided patterns.
    """
    if isinstance(path_patterns, string_types):
        path_patterns = [path_patterns]

    for pattern in path_patterns:
        # Iterate through the provided path patterns
        new_path = pattern
        optional_patterns = re.findall('\[(.*?)\]', pattern)
        # First build from optional patterns if possible
        for optional_pattern in optional_patterns:
            optional_chunk = replace_entities(optional_pattern, entities)
            if optional_chunk:
                new_path = new_path.replace('[%s]' % optional_pattern,
                                            optional_chunk)
            else:
                new_path = new_path.replace('[%s]' % optional_pattern,
                                            '')

        new_path = replace_entities(new_path, entities)
        # Build from required patterns, only return a valid (not None) path
        if new_path:
            return new_path


def write_contents_to_file(path, contents=None, link_to=None,
                           content_mode='text', root=None, conflicts='fail'):
    """
    Uses provided filename patterns to write contents to a new path, given
    a corresponding entity map.

    Args:
        path (str): Destination path of the desired contents.
        contents (str): Raw text or binary encoded string of contents to write
            to the new path.
        link_to (str): Optional path with which to create a symbolic link to.
            Used as an alternative to and takes priority over the contents
            argument.
        content_mode (str): Either 'text' or 'binary' to indicate the writing
            mode for the new file. Only relevant if contents is provided.
        root (str): Optional root directory that all patterns are relative
            to. Defaults to current working directory.
        conflicts (str): One of 'fail', 'skip', 'overwrite', or 'append'
            that defines the desired action when the output path already
            exists. 'fail' raises an exception; 'skip' does nothing;
            'overwrite' overwrites the existing file; 'append' adds a suffix
            to each file copy, starting with 1. Default is 'fail'.
    """
    if not root and not isabs(path):
        root = os.getcwd()

    if root:
        path = join(root, path)

    if exists(path) or islink(path):
        if conflicts == 'fail':
            msg = 'A file at path {} already exists.'
            raise ValueError(msg.format(path))
        elif conflicts == 'skip':
            msg = 'A file at path {} already exists, skipping writing file.'
            logging.warn(msg.format(path))
            return
        elif conflicts == 'overwrite':
            if isdir(path):
                logging.warn('New path is a directory, not going to '
                             'overwrite it, skipping instead.')
                return
            os.remove(path)
        elif conflicts == 'append':
            i = 1
            while i < sys.maxsize:
                path_splits = splitext(path)
                path_splits[0] = path_splits[0] + '_%d' % i
                appended_filename = os.extsep.join(path_splits)
                if not exists(appended_filename) and \
                   not islink(appended_filename):
                    path = appended_filename
                    break
                i += 1
        else:
            raise ValueError('Did not provide a valid conflicts parameter')

    if not exists(dirname(path)):
        os.makedirs(dirname(path))

    if link_to:
        os.symlink(link_to, path)
    elif contents:
        mode = 'wb' if content_mode == 'binary' else 'w'
        with open(path, mode) as f:
            f.write(contents)
    else:
        raise ValueError('One of contents or link_to must be provided.')


class WritableFile(File):

    def __init__(self, filename, path_patterns=None):
        """
        Represents a file that is writable.
        """
        self.path_patterns = path_patterns
        super(WritableFile, self).__init__(filename)

    def build_path(self, path_patterns=None):
        if not path_patterns:
            if self.path_patterns:
                path_patterns = self.path_patterns
            else:
                msg = 'No path patterns specified to build a new path from.'
                raise ValueError(msg)

        return build_path(path_patterns, self.entities)

    def build_file(self, path_patterns=None, symbolic_link=False,
                   root=None, conflicts='fail'):
        new_filename = self.build_path(path_patterns=path_patterns)
        if not new_filename:
            return

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
                               link_to=link_to, content_mode='text',
                               root=root, conflicts=conflicts)


class WritableLayout(Layout):

    def __init__(self, path, path_patterns=None, **kwargs):
        """
        path_patterns (str, list): One or more filename patterns to use
                as a default path pattern for this layout's files. See the
                build_path() method of the File class for more information.
                Can also be specified in the config file.
        """
        self.path_patterns = path_patterns if path_patterns else []
        super(WritableLayout, self).__init__(path, **kwargs)

    def _load_config(self, config):
        config = super(WritableLayout, self)._load_config(config)
        if 'default_path_patterns' in config:
            self.path_patterns += listify(config['default_path_patterns'])
        return config

    def _make_file_object(self, root, f):
        ''' Initialize a new File oject from a directory and filename. Extend
        in subclasses as needed. '''
        return WritableFile(join(root, f), path_patterns=self.path_patterns)

    def write_files(self, files=None, path_patterns=None, symbolic_links=True,
                    root=None, conflicts='fail', **get_selectors):
        """
        Writes desired files to new paths as specified by path_patterns.

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
                'overwrite' overwrites the existing file; 'append' adds a suffix
                to each file copy, starting with 0. Default is 'fail'.
            **get_selectors (kwargs): Optional key word arguments to pass into a
                get() query.
        """
        if files:
            query_files = self.get(return_type='objects', **get_selectors)
            files = list(set(files).intersection(query_files))
        else:
            files = self.get(return_type='objects', **get_selectors)

        for f in files:
            f.build_file(path_patterns=path_patterns,
                         symbolic_link=symbolic_links,
                         root=root,
                         conflicts=conflicts)

    def write_contents_to_file(self, entities, path_patterns=None,
                               contents=None, link_to=None,
                               content_mode='text', conflicts='fail'):
        """
        """
        if not path_patterns:
            path_patterns = self.path_patterns
        path = build_path(path_patterns, entities)
        write_contents_to_file(path, contents=contents, link_to=link_to,
                               content_mode=content_mode, conflicts=conflicts,
                               root=self.root)
        self._index_file(self.root, path)
