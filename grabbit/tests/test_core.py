import pytest
from grabbit import File, Entity, Layout, Tag, merge_layouts
import os
from os.path import join
import posixpath as psp
import tempfile
import json
from copy import copy


DIRNAME = os.path.dirname(__file__)


@pytest.fixture
def file(tmpdir):
    testfile = 'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz'
    fn = tmpdir.mkdir("tmp").join(testfile)
    fn.write('###')
    return File(join(str(fn)))


@pytest.fixture(scope='module', params=['local', 'hdfs'])
def bids_layout(request):
    if request.param == 'local':
        root = join(DIRNAME, 'data', '7t_trt')
        # note about test.json:
        # in this test.json 'subject' regex was left to contain possible
        # leading 0; the other fields (run, session) has leading 0 stripped
        config = join(DIRNAME, 'specs', 'test.json')
        return Layout([(root, config)], regex_search=True)
    else:
        hdfs = pytest.importorskip("hdfs")
        from grabbit.extensions import HDFSLayout
        client = hdfs.Config().get_client()
        root = psp.join('hdfs://localhost:9000{0}'.format(
            client.root), 'data', '7t_trt')
        config = psp.join('hdfs://localhost:9000{0}'.format(
            client.root), 'specs', 'test.json')
        return HDFSLayout([(root, config)], regex_search=True)


@pytest.fixture(scope='module')
def stamp_layout():
    root = join(DIRNAME, 'data', 'valuable_stamps')
    config = join(DIRNAME, 'specs', 'stamps.json')
    return Layout([(root, config)], config_filename='dir_config.json')


@pytest.fixture(scope='module')
def layout_include(request):
    root = join(DIRNAME, 'data', '7t_trt')
    config = join(DIRNAME, 'specs', 'test_include.json')
    return Layout([(root, config)], regex_search=True)


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
        file = copy(file)
        assert file._matches()
        assert file._matches(extensions='nii.gz')
        assert not file._matches(extensions=['.txt', '.rtf'])
        file.tags = {'task': Tag(None, 'rest'), 'run': Tag(None, '2')}
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
        file = copy(file)
        file.tags = {'attrA': Tag(None, 'apple'), 'attrB': Tag(None, 'banana')}
        tup = file.as_named_tuple()
        assert(tup.filename == file.path)
        assert isinstance(tup, tuple)
        assert not hasattr(tup, 'task')
        assert tup.attrA == 'apple'

    def test_named_tuple_with_reserved_name(self, file):
        file = copy(file)
        file.tags['class'] = Tag(None, 'invalid')
        with pytest.warns(UserWarning) as w:
            res = file.as_named_tuple()
            assert w[0].message.args[0].startswith('Entity names cannot')
            assert hasattr(res, 'class_')
            assert not hasattr(res, 'class')


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
        f = File(join(str(tmpdir), filename))
        e = Entity('avaricious', 'aardvark-(\d+)')
        result = e.match_file(f)
        assert result == '4'

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
        assert isinstance(bids_layout.files, dict)
        assert isinstance(bids_layout.entities, dict)
        assert isinstance(bids_layout.mandatory, set)
        assert not bids_layout.dynamic_getters

    def test_init_with_include_arg(self, bids_layout):
        root = join(DIRNAME, 'data', '7t_trt')
        config = join(DIRNAME, 'specs', 'test.json')
        layout = Layout([(root, config)], regex_search=True, include='sub-\d*')
        target = join(root, "dataset_description.json")
        assert target in bids_layout.files
        assert target not in layout.files
        assert join(root, "sub-01", "sub-01_sessions.tsv") in layout.files
        with pytest.raises(ValueError):
            layout = Layout([(root, config)], include='sub-\d*', exclude="meh")

    def test_init_with_exclude_arg(self, bids_layout):
        root = join(DIRNAME, 'data', '7t_trt')
        config = join(DIRNAME, 'specs', 'test.json')
        layout = Layout([(root, config)], regex_search=True, exclude='sub-\d*')
        target = join(root, "dataset_description.json")
        assert target in bids_layout.files
        assert target in layout.files
        sub_file = join(root, "sub-01", "sub-01_sessions.tsv")
        assert sub_file in bids_layout.files
        assert sub_file not in layout.files

    def test_init_with_config_options(self):
        root = join(DIRNAME, 'data')
        dir1 = join(root, 'valuable_stamps')
        dir2 = join(root, 'ordinary_stamps')
        config1 = join(DIRNAME, 'specs', 'stamps.json')
        config2 = join(dir1, 'USA', 'dir_config.json')

        # # Fails because Domain usa_stamps is included twice
        # with pytest.raises(ValueError) as e:
        #     layout = Layout([(root, [config1, config2])], exclude=['7t_trt'],
        #                     config_filename='dir_config.json')
        #     print(dir(e))
        #     assert e.value.message.startswith('Config with name')

        # Test with two configs
        layout = Layout([(root, [config1, config2])], exclude=['7t_trt'])
        files = [f.filename for f in layout.files.values()]
        assert 'name=Inverted_Jenny#value=75000#country=USA.txt' in files
        assert 'name=5c_Francis_E_Willard#value=1dollar.txt' in files
        assert 'name=1_Lotus#value=1#country=Canada.txt' in files

        # Test with two configs and on-the-fly directory remapping
        layout = Layout([dir1, ([dir1, dir2], config1)],
                        exclude=['USA/'])
        files = [f.filename for f in layout.files.values()]
        assert 'name=Inverted_Jenny#value=75000#country=USA.txt' in files
        assert 'name=5c_Francis_E_Willard#value=1dollar.txt' not in files
        assert 'name=1_Lotus#value=1#country=Canada.txt' in files

    def test_absolute_paths(self, bids_layout):

        if not hasattr(bids_layout, '_hdfs_client'):
            root = join(DIRNAME, 'data', '7t_trt')
            root = os.path.relpath(root)
            config = join(DIRNAME, 'specs', 'test.json')

            layout = Layout([(root, config)], absolute_paths=True)
            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

            layout = Layout([(root, config)], absolute_paths=False)
            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert not any([os.path.isabs(f.filename) for f in result])

        # Should always be absolute paths on HDFS
        else:
            root = psp.join('hdfs://localhost:9000{0}'.format(
                layout._hdfs_client.root), 'data', '7t_trt')
            config = psp.join('hdfs://localhost:9000{0}'.format(
                layout._hdfs_client.root), 'specs', 'test.json')

            layout = Layout([(root, config)], absolute_paths=False)

            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

            layout = Layout([(root, config)], absolute_paths=True)
            result = layout.get(subject=1, run=1, session=1)
            assert result
            assert all([os.path.isabs(f.filename) for f in result])

    @pytest.mark.parametrize('data_dir, config',
                             [(join(DIRNAME, 'data', '7t_trt'),
                               join(DIRNAME, 'specs', 'test.json')),
                              (psp.join('hdfs://localhost:9000/grabbit/test/',
                               'data', '7t_trt'),
                               psp.join('hdfs://localhost:9000/grabbit/test/',
                               'specs', 'test.json'))])
    def test_dynamic_getters(self, data_dir, config):

        if ('hdfs' in data_dir or 'hdfs' in config):
            pytest.importorskip('hdfs')

        layout = Layout([(data_dir, config)], dynamic_getters=True)
        assert hasattr(layout, 'get_subjects')
        assert '01' in getattr(layout, 'get_subjects')()
        assert 1 in getattr(layout, 'get_runs')()

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
        assert result[0].run == 1

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
            assert os.path.exists(join(bids_layout.root, result[0]))
            assert os.path.isdir(join(bids_layout.root, result[0]))

        result = bids_layout.get(target='subject', type='phasediff',
                                 return_type='file')

        if hasattr(bids_layout, '_hdfs_client'):
            assert all([bids_layout._hdfs_client.content(f) for f in result])
        else:
            assert all([os.path.exists(join(bids_layout.root, f))
                        for f in result])

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
        target = join('sub-01', 'sub-01_sessions.tsv')
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

        # Check for file with matching run (fails if types don't match)
        nearest = bids_layout.get_nearest(
            result, type='phasediff', extensions='.nii.gz')
        assert nearest is not None
        assert os.path.basename(nearest) == 'sub-01_ses-1_run-1_phasediff.nii.gz'

    def test_index_regex(self, bids_layout, layout_include):
        targ = join('derivatives', 'excluded.json')
        assert targ not in bids_layout.files
        domain = layout_include.domains['test_with_includes']
        targ = join('models', 'excluded_model.json')
        assert targ not in domain.files

    def test_save_index(self, bids_layout):
        tmp = tempfile.mkstemp(suffix='.json')[1]
        bids_layout.save_index(tmp)
        assert os.path.exists(tmp)
        with open(tmp, 'r') as infile:
            index = json.load(infile)
        assert len(index) == len(bids_layout.files)
        # Check that entities for first 10 files match
        files = list(bids_layout.files.values())
        for i in range(10):
            f = files[i]
            entities = {v.entity.id: v.value for v in f.tags.values()}
            assert entities == index[f.path]['entities']
            assert list(f.domains) == index[f.path]['domains']
        os.unlink(tmp)

    def test_load_index(self, bids_layout):
        f = join(DIRNAME, 'misc', 'index.json')
        bids_layout.load_index(f)
        assert bids_layout.unique('subject') == ['01']
        assert len(bids_layout.files) == 24

        # Test with reindexing
        f = join(DIRNAME, 'misc', 'index.json')
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

        root = join(DIRNAME, 'data', '7t_trt')
        config = join(DIRNAME, 'specs', 'test_with_mapper.json')

        # Test with external mapper
        em = EntityMapper()
        layout = Layout([(root, config)], regex_search=True, entity_mapper=em)
        f = list(layout.files.values())[20]
        assert hash(f.path) == f.entities['hash']

        # Test with mapper set to self
        layout = MappingLayout([(root, config)], regex_search=True,
                               entity_mapper='self')
        f = list(layout.files.values())[10]
        assert str(hash(f.path)) + '.hsh' == f.entities['hash']

        # Should fail if we use a spec with entities that have mappers but
        # don't specify an entity-mapping object
        with pytest.raises(ValueError):
            layout = Layout([(root, config)], regex_search=True)

    def test_clone(self, bids_layout):
        lc = bids_layout.clone()
        attrs = ['mandatory', 'dynamic_getters', 'regex_search',
                 'entity_mapper']
        for a in attrs:
            assert getattr(bids_layout, a) == getattr(lc, a)
        assert set(bids_layout.files.keys()) == set(lc.files.keys())
        assert set(bids_layout.entities.keys()) == set(lc.entities.keys())

    def test_excludes(self, tmpdir):
        root = tmpdir.mkdir("ohmyderivatives").mkdir("ds")
        config = join(DIRNAME, 'specs', 'test.json')
        layout = Layout([(str(root), config)], regex_search=True)
        assert not layout._check_inclusions(
            str(root.join("badbadderivatives")))

    def test_multiple_domains(self, stamp_layout):
        layout = stamp_layout.clone()
        assert {'stamps', 'usa_stamps'} == set(layout.domains.keys())
        usa = layout.domains['usa_stamps']
        general = layout.domains['stamps']
        assert len(usa.files) == 3
        assert len(layout.files) == len(general.files)
        assert not set(usa.files) - set(general.files)
        assert layout.entities['usa_stamps.name'] == usa.entities['name']
        assert layout.entities['stamps.name'] == general.entities['name']
        assert usa.entities['name'] != general.entities['name']
        f = layout.get(name='5c_Francis_E_Willard', return_type='obj')[0]
        assert f.entities == {'name': '5c_Francis_E_Willard',
                              'value': '1dollar'}

    def test_get_by_domain(self, stamp_layout):
        files = stamp_layout.get(domains='usa_stamps')
        assert len(files) == 3
        files = stamp_layout.get(domains=['nonexistent', 'doms'])
        assert not files
        files = stamp_layout.get(domains='usa_stamps', value='35',
                                 regex_search=True)
        assert len(files) == 1
        files = stamp_layout.get(value='35', regex_search=True)
        assert len(files) == 2

    def test_parse_file_entities(self, bids_layout):
        filename = 'sub-03_ses-07_run-4_sekret.nii.gz'
        with pytest.raises(ValueError):
            bids_layout.parse_file_entities(filename)
        ents = bids_layout.parse_file_entities(filename, domains=['test'])
        assert ents == {'subject': '03', 'session': '7', 'run': 4,
                        'type': 'sekret'}


def test_merge_layouts(bids_layout, stamp_layout):
    layout = merge_layouts([bids_layout, stamp_layout])
    assert len(layout.files) == len(bids_layout.files) + \
        len(stamp_layout.files)
    assert 'stamps.country' in layout.entities
    assert 'test.subject' in layout.entities
    dom = layout.domains['stamps']
    assert 'country' in dom.entities
    dom = layout.domains['test']
    assert 'subject' in dom.entities

    # Make sure first Layout was cloned and not passed by reference
    patt = layout.entities['test.subject'].pattern
    assert patt == bids_layout.entities['test.subject'].pattern
    bids_layout.entities['test.subject'].pattern = "meh"
    assert patt != "meh"
