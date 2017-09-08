import pytest
from grabbit import File, Entity, Layout
import os
import posixpath as psp
import json

@pytest.fixture
def file(tmpdir):
    testfile = 'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz'
    fn = tmpdir.mkdir("tmp").join(testfile)
    fn.write('###')
    return File(os.path.join(str(fn)))

@pytest.fixture(scope='module', params=['local', 'hdfs'])
def layout(request):
    if request.param == 'local':
        root = os.path.join(os.path.dirname(__file__), 'data', '7t_trt')
        # note about test.json:
        #  in this test.json 'subject' regex was left to contain possible leading 0
        #  the other fields (run, session) has leading 0 stripped
        config = os.path.join(os.path.dirname(__file__), 'specs', 'test.json')
    else:
        hdfs = pytest.importorskip("hdfs")
        client = hdfs.Config().get_client()
        root = psp.join('hdfs://localhost:9000{0}'.format(client.root), 'data', '7t_trt')
        config = psp.join('hdfs://localhost:9000{0}'.format(client.root), 'specs', 'test.json')

    return Layout(root, config, regex_search=True)

@pytest.fixture(scope='module', params=['local', 'hdfs'])
def layout2(request):
    if request.param == 'local':
        root = os.path.join(os.path.dirname(__file__), 'data', '7t_trt')
        config = os.path.join(os.path.dirname(__file__), 'specs', 'test_include.json')
    else:
        hdfs = pytest.importorskip("hdfs")
        client = hdfs.Config().get_client()
        root = psp.join('hdfs://localhost:9000{0}'.format(client.root), 'data', '7t_trt')
        config = psp.join('hdfs://localhost:9000{0}'.format(client.root), 'specs', 'test_include.json')
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

    def test_init(self, layout):
        if layout._hdfs_client is None:
            assert os.path.exists(layout.root)
        else:
            assert layout._hdfs_client.list(layout.root)
        assert isinstance(layout.files, dict)
        assert isinstance(layout.entities, dict)
        assert isinstance(layout.mandatory, set)
        assert not layout.dynamic_getters

    def test_absolute_paths(self, layout):
        result = layout.get(subject=1, run=1, session=1)
        assert result  # that we got some entries
        assert all([os.path.isabs(f.filename) for f in result])

        if layout._hdfs_client is None:
            root = os.path.join(os.path.dirname(__file__), 'data', '7t_trt')
            root = os.path.relpath(root)
            config = os.path.join(os.path.dirname(__file__), 'specs', 'test.json')

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
            root = psp.join('hdfs://localhost:9000{0}'.format(layout._hdfs_client.root), 'data', '7t_trt')
            config = psp.join('hdfs://localhost:9000{0}'.format(layout._hdfs_client.root), 'specs', 'test.json') 

            layout = Layout(root, config, absolute_paths=False)

            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

            layout = Layout(root, config, absolute_paths=True)
            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

    
    @pytest.mark.parametrize('data_dir, config', 
                                [(os.path.join(os.path.dirname(__file__), 'data', '7t_trt'), 
                                 os.path.join(os.path.dirname(__file__), 'specs', 'test.json')), 
                                (psp.join('hdfs://localhost:9000/grabbit/test/', 'data', '7t_trt'), 
                                psp.join('hdfs://localhost:9000/grabbit/test/', 'specs', 'test.json'))])
    def test_dynamic_getters(self, data_dir, config):
        
         
        if ('hdfs' in data_dir or 'hdfs' in config):
            pytest.importorskip('hdfs')
            
        layout = Layout(data_dir, config, dynamic_getters=True)
        assert hasattr(layout, 'get_subjects')
        assert '01' in getattr(layout, 'get_subjects')()

    def test_querying(self, layout):

        # With regex_search = True (as set in Layout())
        result = layout.get(subject=1, run=1, session=1, extensions='nii.gz')
        assert len(result) == 8
        result = layout.get(subject='01', run=1, session=1, type='phasediff',
                            extensions='.json')
        assert len(result) == 1
        assert 'phasediff.json' in result[0].filename
        assert hasattr(result[0], 'run')
        assert result[0].run == '1'

        # With exact matching...
        result = layout.get(subject='1', run=1, session=1, extensions='nii.gz',
                            regex_search=False)
        assert len(result) == 0

        result = layout.get(target='subject', return_type='id')
        assert len(result) == 10
        assert '03' in result
        result = layout.get(target='subject', return_type='dir')

        if layout._hdfs_client is None:
            assert os.path.exists(result[0])
            assert os.path.isdir(result[0])
        else:
            assert layout._hdfs_client.list(layout.root)

        result = layout.get(target='subject', type='phasediff', return_type='file')
        
        if layout._hdfs_client is None:
            assert all([os.path.exists(f) for f in result])
        else:
            assert all([layout._hdfs_client.content(f) for f in result])

    def test_natsort(self, layout):
        result = layout.get(target='subject', return_type='id')
        assert result[:5] == list(map("%02d".__mod__ , range(1, 6)))

    def test_unique_and_count(self, layout):
        result = layout.unique('subject')
        assert len(result) == 10
        assert '03' in result
        assert layout.count('run') == 2
        assert layout.count('run', files=True) > 2

    def test_get_nearest(self, layout):
        result = layout.get(subject='01', run=1, session=1, type='phasediff',
                            extensions='.json', return_type='file')[0]
        nearest = layout.get_nearest(result, type='sessions', extensions='tsv',
                                     ignore_strict_entities=['type'])
        assert '7t_trt/sub-01/sub-01_sessions.tsv' in nearest
        nearest = layout.get_nearest(result, extensions='tsv', all_=True,
                                     ignore_strict_entities=['type'])
        assert len(nearest) == 3
        nearest = layout.get_nearest(result, extensions='tsv', all_=True,
                                     return_type='tuple',
                                     ignore_strict_entities=['type'])
        assert len(nearest) == 3
        assert nearest[0].subject == '01'

    def test_index_regex(self, layout, layout2):
        assert os.path.join(
            layout.root, 'derivatives/excluded.json') not in layout.files
        assert os.path.join(
            layout2.root, 'models/excluded_model.json') not in layout2.files

        with pytest.raises(ValueError):
            layout2._load_config({'entities' : [],
                                  'index' : {'include' : 'test',
                                             'exclude' : 'test'}})
