import pytest
from grabbit import File, Entity, Layout, merge_layouts
import os
import posixpath as psp
import tempfile
import json


DIRNAME = os.path.dirname(__file__)


@pytest.fixture
def file(tmpdir):
    testfile = 'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz'
    fn = tmpdir.mkdir("tmp").join(testfile)
    fn.write('###')
    return File(os.path.join(str(fn)))


@pytest.fixture(scope='module', params=['local', 'hdfs'])
def bids_layout(request):
    if request.param == 'local':
        root = os.path.join(DIRNAME, 'data', '7t_trt')
        # note about test.json:
        # in this test.json 'subject' regex was left to contain possible
        # leading 0; the other fields (run, session) has leading 0 stripped
        config = os.path.join(DIRNAME, 'specs', 'test.json')
        return Layout(root, config, regex_search=True)
    else:
        hdfs = pytest.importorskip("hdfs")
        from grabbit.extensions import HDFSLayout
        client = hdfs.Config().get_client()
        root = psp.join('hdfs://localhost:9000{0}'.format(client.root), 'data', '7t_trt')
        config = psp.join('hdfs://localhost:9000{0}'.format(client.root), 'specs', 'test.json')
        return HDFSLayout(root, config, regex_search=True)

@pytest.fixture(scope='module')
def stamp_layout():
    root = os.path.join(DIRNAME, 'data', 'valuable_stamps')
    config = os.path.join(DIRNAME, 'specs', 'stamps.json')
    return Layout(root, config)


@pytest.fixture(scope='module')
def layout_include(request):
    root = os.path.join(DIRNAME, 'data', '7t_trt')
    config = os.path.join(DIRNAME, 'specs', 'test_include.json')
    return Layout(root, config, regex_search=True)


class TestFile:

    def test_init(self, tmpdir):
        fn = tmpdir.mkdir("tmp").join('tmp.txt')
        fn.write('###')
        f = File(str(fn))
        assert os.path.exists(f.path)
        assert f.filename is not None
        assert os.path.isdir(f.dirname)
        assert f.entities == {}

    def test_matches(self, file):
        assert file._matches()
        assert file._matches(extensions='nii.gz')
        assert not file._matches(extensions=['.txt', '.rtf'])
        file.entities = {'task': 'rest', 'run': '2'}
        assert file._matches(entities={'task': 'rest', 'run': 2})
        assert not file._matches(entities={'task': 'rest', 'run': 4})
        assert not file._matches(entities={'task': 'st'})
        assert file._matches(entities={'task': 'st'}, regex_search=True)
        # With list of matches
        assert not file._matches(entities={'task': ['A', 'B', 'C']})
        assert file._matches(entities={'task': ['A', 'B', 'rest']})
        assert file._matches(entities={'task': ['A', 'B', 'st']},
                             regex_search=True)

    def test_named_tuple(self, file):
        file.entities = {'attrA': 'apple', 'attrB': 'banana'}
        tup = file.as_named_tuple()
        assert(tup.filename == file.path)
        assert isinstance(tup, tuple)
        assert not hasattr(tup, 'task')
        assert tup.attrA == 'apple'


class TestEntity:

    def test_init(self):
        e = Entity('avaricious', 'aardvark-(\d+)')
        assert e.name == 'avaricious'
        assert e.pattern == 'aardvark-(\d+)'
        assert not e.mandatory
        assert e.directory is None
        assert e.files == {}

    def test_matches(self, tmpdir):
        filename = "aardvark-4-reporting-for-duty.txt"
        tmpdir.mkdir("tmp").join(filename).write("###")
        f = File(os.path.join(str(tmpdir), filename))
        e = Entity('avaricious', 'aardvark-(\d+)')
        e.matches(f)
        assert 'avaricious' in f.entities
        assert f.entities['avaricious'] == '4'

    def test_unique_and_count(self):
        e = Entity('prop', '-(\d+)')
        e.files = {
            'test1-10.txt': '10',
            'test2-7.txt': '7',
            'test3-7.txt': '7'
        }
        assert sorted(e.unique()) == ['10', '7']
        assert e.count() == 2
        assert e.count(files=True) == 3

    def test_add_file(self):
        e = Entity('prop', '-(\d+)')
        e.add_file('a', '1')
        assert e.files['a'] == '1'


class TestLayout:

    def test_init(self, bids_layout):
        if hasattr(bids_layout, '_hdfs_client'):
            assert bids_layout._hdfs_client.list(bids_layout.root)
        else:
            assert os.path.exists(bids_layout.root)
        assert isinstance(bids_layout.files, dict)
        assert isinstance(bids_layout.entities, dict)
        assert isinstance(bids_layout.mandatory, set)
        assert not bids_layout.dynamic_getters

    def test_absolute_paths(self, bids_layout):
        result = bids_layout.get(subject=1, run=1, session=1)
        assert result  # that we got some entries
        assert all([os.path.isabs(f.filename) for f in result])

        if not hasattr(bids_layout, '_hdfs_client'):
            root = os.path.join(DIRNAME, 'data', '7t_trt')
            root = os.path.relpath(root)
            config = os.path.join(DIRNAME, 'specs', 'test.json')

            layout = Layout(root, config, absolute_paths=False)

            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert not any([os.path.isabs(f.filename) for f in result])

            layout = Layout(root, config, absolute_paths=True)
            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

        # Should always be absolute paths on HDFS
        else:
            root = psp.join('hdfs://localhost:9000{0}'.format(
                layout._hdfs_client.root), 'data', '7t_trt')
            config = psp.join('hdfs://localhost:9000{0}'.format(
                layout._hdfs_client.root), 'specs', 'test.json')

            layout = Layout(root, config, absolute_paths=False)

            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

            layout = Layout(root, config, absolute_paths=True)
            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

    @pytest.mark.parametrize('data_dir, config',
                             [(os.path.join(DIRNAME, 'data', '7t_trt'),
                               os.path.join(DIRNAME, 'specs', 'test.json')),
                              (psp.join('hdfs://localhost:9000/grabbit/test/',
                               'data', '7t_trt'),
                               psp.join('hdfs://localhost:9000/grabbit/test/',
                               'specs', 'test.json'))])
    def test_dynamic_getters(self, data_dir, config):

        if ('hdfs' in data_dir or 'hdfs' in config):
            pytest.importorskip('hdfs')

        layout = Layout(data_dir, config, dynamic_getters=True)
        assert hasattr(layout, 'get_subjects')
        assert '01' in getattr(layout, 'get_subjects')()

    def test_querying(self, bids_layout):

        # With regex_search = True (as set in Layout())
        result = bids_layout.get(subject=1, run=1, session=1,
                                 extensions='nii.gz')
        assert len(result) == 8
        result = bids_layout.get(subject='01', run=1, session=1,
                                 type='phasediff', extensions='.json')
        assert len(result) == 1
        assert 'phasediff.json' in result[0].filename
        assert hasattr(result[0], 'run')
        assert result[0].run == '1'

        # With exact matching...
        result = bids_layout.get(subject='1', run=1, session=1,
                                 extensions='nii.gz', regex_search=False)
        assert len(result) == 0

        result = bids_layout.get(target='subject', return_type='id')
        assert len(result) == 10
        assert '03' in result
        result = bids_layout.get(target='subject', return_type='dir')

        if hasattr(bids_layout, '_hdfs_client'):
            assert bids_layout._hdfs_client.list(bids_layout.root)
        else:
            assert os.path.exists(result[0])
            assert os.path.isdir(result[0])

        result = bids_layout.get(target='subject', type='phasediff',
                                 return_type='file')

        if hasattr(bids_layout, '_hdfs_client'):
            assert all([bids_layout._hdfs_client.content(f) for f in result])
        else:
            assert all([os.path.exists(f) for f in result])

    def test_natsort(self, bids_layout):
        result = bids_layout.get(target='subject', return_type='id')
        assert result[:5] == list(map("%02d".__mod__, range(1, 6)))

    def test_unique_and_count(self, bids_layout):
        result = bids_layout.unique('subject')
        assert len(result) == 10
        assert '03' in result
        assert bids_layout.count('run') == 2
        assert bids_layout.count('run', files=True) > 2

    def test_get_nearest(self, bids_layout):
        result = bids_layout.get(
            subject='01', run=1, session=1, type='phasediff',
            extensions='.json', return_type='file')[0]
        nearest = bids_layout.get_nearest(
            result, type='sessions', extensions='tsv',
            ignore_strict_entities=['type'])
        target = os.path.join('7t_trt', 'sub-01', 'sub-01_sessions.tsv')
        assert target in nearest
        nearest = bids_layout.get_nearest(
            result, extensions='tsv', all_=True,
            ignore_strict_entities=['type'])
        assert len(nearest) == 3
        nearest = bids_layout.get_nearest(
            result, extensions='tsv', all_=True, return_type='tuple',
            ignore_strict_entities=['type'])
        assert len(nearest) == 3
        assert nearest[0].subject == '01'

    def test_index_regex(self, bids_layout, layout_include):
        targ = os.path.join(bids_layout.root, 'derivatives', 'excluded.json')
        assert targ not in bids_layout.files
        targ = os.path.join(layout_include.root, 'models',
                            'excluded_model.json')
        assert targ not in layout_include.files

        with pytest.raises(ValueError):
            layout_include._load_config({'entities': [],
                                         'index': {'include': 'test',
                                                   'exclude': 'test'}})

    def test_save_index(self, bids_layout):
        tmp = tempfile.mkstemp(suffix='.json')[1]
        bids_layout.save_index(tmp)
        assert os.path.exists(tmp)
        with open(tmp, 'r') as infile:
            index = json.load(infile)
        assert len(index) == len(bids_layout.files)
        # Check that entities for first 10 files match
        for i in range(10):
            f = list(bids_layout.files.values())[i]
            assert f.entities == index[f.path]
        os.unlink(tmp)

    def test_load_index(self, bids_layout):
        f = os.path.join(DIRNAME, 'misc', 'index.json')
        bids_layout.load_index(f)
        assert bids_layout.unique('subject') == ['01']
        assert len(bids_layout.files) == 24

        # Test with reindexing
        f = os.path.join(DIRNAME, 'misc', 'index.json')
        bids_layout.load_index(f, reindex=True)
        assert bids_layout.unique('subject') == ['01']
        assert len(bids_layout.files) == 24

    def test_entity_mapper(self):

        class EntityMapper(object):
            def hash_file(self, file):
                return hash(file.path)

        class MappingLayout(Layout):
            def hash_file(self, file):
                return str(hash(file.path)) + '.hsh'

        root = os.path.join(DIRNAME, 'data', '7t_trt')
        config = os.path.join(DIRNAME, 'specs',
                              'test_with_mapper.json')

        # Test with external mapper
        em = EntityMapper()
        layout = Layout(root, config, regex_search=True, entity_mapper=em)
        f = list(layout.files.values())[20]
        assert hash(f.path) == f.entities['hash']

        # Test with mapper set to self
        layout = MappingLayout(root, config, regex_search=True,
                               entity_mapper='self')
        f = list(layout.files.values())[10]
        assert str(hash(f.path)) + '.hsh' == f.entities['hash']

        # Should fail if we use a spec with entities that have mappers but
        # don't specify an entity-mapping object
        with pytest.raises(ValueError):
            layout = Layout(root, config, regex_search=True)

    def test_clone(self, bids_layout):
        lc = bids_layout.clone()
        attrs = ['root', 'mandatory', 'dynamic_getters', 'regex_search',
                 'filtering_regex', 'entity_mapper']
        for a in attrs:
            assert getattr(bids_layout, a) == getattr(lc, a)
        assert set(bids_layout.files.keys()) == set(lc.files.keys())
        assert set(bids_layout.entities.keys()) == set(lc.entities.keys())

    def test_excludes(self, tmpdir):
        root = tmpdir.mkdir("ohmyderivatives").mkdir("ds")
        config = os.path.join(DIRNAME, 'specs', 'test.json')
        layout = Layout(str(root), config, regex_search=True)
        assert layout._check_inclusions(str(root.join("ohmyimportantfile")))
        assert not layout._check_inclusions(str(root.join("badbadderivatives")))


def test_merge_layouts(bids_layout, stamp_layout):
    layout = merge_layouts([bids_layout, stamp_layout])
    assert len(layout.files) == len(bids_layout.files) + \
        len(stamp_layout.files)
    assert 'country' in layout.entities
    assert 'subject' in layout.entities

    # Make sure first Layout was cloned and not passed by reference
    patt = layout.entities['subject'].pattern
    assert patt == bids_layout.entities['subject'].pattern
    bids_layout.entities['subject'].pattern = "meh"
    assert patt != "meh"
