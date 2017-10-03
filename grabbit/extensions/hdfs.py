from grabbit import Layout, File
from grabbit.external import six
from hdfs import Config
import posixpath as psp
from os.path import abspath
import json


class HDFSLayout(Layout):

    def __init__(self, path, config=None, dynamic_getters=False,
                 absolute_paths=True, regex_search=False):
        """
        A container for all the files and metadata found at the specified path.
        Args:
            path (str): The root path of the layout.
            config (str): The path to the JSON config file that defines the
            entities and paths for the current layout.
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
        """
        self._hdfs_client = Config().get_client()

        path = abspath(path) if absolute_paths and self._hdfs_client is None \
            else path

        # Preprocess the config file
        if isinstance(config, six.string_types):
            config = '/'.join(config.strip('hdfs://').split('/')[1:])
            config = config.replace(self._hdfs_client.root[1:], '')
            with self._hdfs_client.read(config) as reader:
                config = json.load(reader)

        super(HDFSLayout, self).__init__(path, config, dynamic_getters,
                                         absolute_paths, regex_search)

    def _get_files(self):
        self.root = '/'.join(self.root.strip('hdfs://').split('/')
                             [1:]).replace(self._hdfs_client.root[1:], '')
        return self._hdfs_client.walk(self.root)

    def _make_file_object(self, root, f):
        filepath = str(psp.join(root, f))
        with self._hdfs_client.read(filepath):
            return File(filepath)
