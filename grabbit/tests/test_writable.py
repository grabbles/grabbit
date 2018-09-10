import pytest
from grabbit import Layout, File, Tag
from grabbit.extensions.writable import build_path
import os
import shutil
from os.path import join, exists, islink, dirname


@pytest.fixture
def writable_file(tmpdir):
    testfile = 'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz'
    fn = tmpdir.mkdir("tmp").join(testfile)
    fn.write('###')
    return File(os.path.join(str(fn)))


@pytest.fixture
def layout():
    data_dir = join(dirname(__file__), 'data', '7t_trt')
    config = join(dirname(__file__), 'specs', 'test.json')
    layout = Layout([(data_dir, config)], absolute_paths=False,
                    root=data_dir)
    return layout


class TestWritableFile:

    def test_build_path(self, writable_file):
        writable_file.tags = {
            'task': Tag(None, 'rest'), 'run': Tag(None, '2'),
            'subject': Tag(None, '3')
        }

        # Single simple pattern
        with pytest.raises(TypeError):
            build_path(writable_file.entities)
        pat = join(writable_file.dirname,
                   '{task}/sub-{subject}/run-{run}.nii.gz')
        target = join(writable_file.dirname, 'rest/sub-3/run-2.nii.gz')
        assert build_path(writable_file.entities, pat) == target

        # Multiple simple patterns
        pats = ['{session}/{task}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz',
                '{subject}/{task}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 't-rest/3-2.nii.gz')
        assert build_path(writable_file.entities, pats) == target

        # Pattern with optional entity
        pats = ['[{session}/]{task}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 'rest/r-2.nii.gz')
        assert build_path(writable_file.entities, pats) == target

        # Pattern with conditional values
        pats = ['{task<func|acq>}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 't-rest/3-2.nii.gz')
        assert build_path(writable_file.entities, pats) == target

        # Pattern with valid conditional values
        pats = ['{task<func|rest>}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 'rest/r-2.nii.gz')
        assert build_path(writable_file.entities, pats) == target

        # Pattern with optional entity with conditional values
        pats = ['[{task<func|acq>}/]r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz']
        pats = [join(writable_file.dirname, p) for p in pats]
        target = join(writable_file.dirname, 'r-2.nii.gz')
        assert build_path(writable_file.entities, pats) == target

        # Pattern with default value
        pats = ['sess-{session|A}/r-{run}.nii.gz']
        assert build_path({'run': 3}, pats) == 'sess-A/r-3.nii.gz'

        # Pattern with both valid and default values
        pats = ['sess-{session<A|B|C>|D}/r-{run}.nii.gz']
        assert build_path({'session': 1, 'run': 3}, pats) == 'sess-D/r-3.nii.gz'
        pats = ['sess-{session<A|B|C>|D}/r-{run}.nii.gz']
        assert build_path({'session': 'B', 'run': 3}, pats) == 'sess-B/r-3.nii.gz'

    def test_strict_build_path(self):

        # Test with strict matching--should fail
        pats = ['[{session}/]{task}/r-{run}.nii.gz',
                't-{task}/{subject}-{run}.nii.gz']
        entities = {'subject': 1, 'task': "A", 'run': 2}
        assert build_path(entities, pats, True)
        entities = {'subject': 1, 'task': "A", 'age': 22}
        assert not build_path(entities, pats, True)

    def test_build_file(self, writable_file, tmpdir, caplog):
        writable_file.tags = {'task': Tag(None, 'rest'), 'run': Tag(None, '2'),
                              'subject': Tag(None, '3')}

        # Simple write out
        new_dir = join(writable_file.dirname, 'rest')
        pat = join(writable_file.dirname,
                   '{task}/sub-{subject}/run-{run}.nii.gz')
        target = join(writable_file.dirname, 'rest/sub-3/run-2.nii.gz')
        writable_file.copy(pat)
        assert exists(target)

        # Conflict handling
        with pytest.raises(ValueError):
            writable_file.copy(pat)
        with pytest.raises(ValueError):
            writable_file.copy(pat, conflicts='fail')
        writable_file.copy(pat, conflicts='skip')
        log_message = caplog.records[0].message
        assert log_message == 'A file at path {} already exists, ' \
                              'skipping writing file.'.format(target)
        writable_file.copy(pat, conflicts='append')
        append_target = join(writable_file.dirname,
                             'rest/sub-3/run-2_1.nii.gz')
        assert exists(append_target)
        writable_file.copy(pat, conflicts='overwrite')
        assert exists(target)
        shutil.rmtree(new_dir)

        # Symbolic linking
        writable_file.copy(pat, symbolic_link=True)
        assert islink(target)
        shutil.rmtree(new_dir)

        # Using different root
        root = str(tmpdir.mkdir('tmp2'))
        pat = join(root, '{task}/sub-{subject}/run-{run}.nii.gz')
        target = join(root, 'rest/sub-3/run-2.nii.gz')
        writable_file.copy(pat, root=root)
        assert exists(target)

        # Copy into directory functionality
        pat = join(writable_file.dirname, '{task}/')
        writable_file.copy(pat)
        target = join(writable_file.dirname, 'rest', writable_file.filename)
        assert exists(target)
        shutil.rmtree(new_dir)


class TestWritableLayout:

    def test_write_files(self, tmpdir, layout):

        pat = join(str(tmpdir), 'sub-{subject<01|02>}'
                                '/sess-{session}'
                                '/r-{run}'
                                '/type-{type}'
                                '/task-{task}.nii.gz')
        layout.copy_files(path_patterns=pat)
        example_file = join(str(tmpdir), 'sub-02'
                                         '/sess-2'
                                         '/r-1'
                                         '/type-bold'
                                         '/task-rest.nii.gz')
        example_file2 = join(str(tmpdir), 'sub-04'
                                          '/sess-2'
                                          '/r-1'
                                          '/type-bold'
                                          '/task-rest.nii.gz')

        assert exists(example_file)
        assert not exists(example_file2)

        pat = join(str(tmpdir), 'sub-{subject}'
                                '/sess-{session}'
                                '/r-{run}'
                                '/type-{type}'
                                '/task-{task}.nii.gz')
        layout.copy_files(path_patterns=pat, conflicts='overwrite')
        example_file = join(str(tmpdir), 'sub-02'
                                         '/sess-2'
                                         '/r-1'
                                         '/type-bold'
                                         '/task-rest.nii.gz')
        assert exists(example_file)
        assert exists(example_file2)

    def test_write_contents_to_file(self, layout):
        contents = 'test'
        data_dir = join(dirname(__file__), 'data', '7t_trt')
        entities = {'subject': 'Bob', 'session': '01'}
        pat = join('sub-{subject}/sess-{session}/desc.txt')

        # With indexing
        layout.write_contents_to_file(entities, path_patterns=pat,
                                      contents=contents, index=True)
        target = join(data_dir, 'sub-Bob/sess-01/desc.txt')
        assert exists(target)
        with open(target) as f:
            written = f.read()
        assert written == contents
        assert target in layout.files
        shutil.rmtree(join(data_dir, 'sub-Bob'))

        # Without indexing
        pat = join('sub-{subject}/sess-{session}/desc_no_index.txt')
        layout.write_contents_to_file(entities, path_patterns=pat,
                                      contents=contents, index=False)
        target = join(data_dir, 'sub-Bob/sess-01/desc_no_index.txt')
        assert exists(target)
        with open(target) as f:
            written = f.read()
        assert written == contents
        assert target not in layout.files
        shutil.rmtree(join(data_dir, 'sub-Bob'))

    def test_write_contents_to_file_defaults(self, layout):
        contents = 'test'
        data_dir = join(dirname(__file__), 'data', '7t_trt')
        config = join(dirname(__file__), 'specs', 'test.json')
        layout = Layout([(data_dir, [config, {
            'name': "test_writable",
            'default_path_patterns': ['sub-{subject}/ses-{session}/{subject}'
                                      '{session}{run}{type}{task}{acquisition}'
                                      '{bval}']
        }])], root=data_dir)
        entities = {'subject': 'Bob', 'session': '01', 'run': '1',
                    'type': 'test', 'task': 'test', 'acquisition': 'test',
                    'bval': 0}
        layout.write_contents_to_file(entities, contents=contents, index=True)
        target = join(data_dir, 'sub-Bob/ses-01/Bob011testtesttest0')
        assert exists(target)
        with open(target) as f:
            written = f.read()
        assert written == contents
        assert target in layout.files
        shutil.rmtree(join(data_dir, 'sub-Bob'))

    def test_build_file_from_layout(self, tmpdir, layout):
        entities = {'subject': 'Bob', 'session': '01', 'run': '1'}
        pat = join(str(tmpdir), 'sub-{subject}'
                   '/sess-{session}'
                   '/r-{run}.nii.gz')
        path = layout.build_path(entities, path_patterns=pat)
        assert path == join(str(tmpdir), 'sub-Bob/sess-01/r-1.nii.gz')

        data_dir = join(dirname(__file__), 'data', '7t_trt')
        filename = 'sub-04_ses-1_task-rest_acq-fullbrain_run-1_physio.tsv.gz'
        file = join('sub-04', 'ses-1', 'func', filename)
        path = layout.build_path(file, path_patterns=pat)
        assert path.endswith('sub-04/sess-1/r-1.nii.gz')
