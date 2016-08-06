import pytest
from grabbit import File, Entity, Layout
import os
from pprint import pprint


@pytest.fixture
def file():
    path = os.path.join(os.path.dirname(__file__), 'data', '7t_trt', 'sub-03',
                         'ses-2', 'func',
                         'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz')
    return(File(path))


class TestFile:

    def test_init(self):
        path = os.path.join(os.path.dirname(__file__), 'data', '7t_trt',
                            'sub-03', 'ses-2', 'func',
                            'sub-03_ses-2_task-rest_acq-fullbrain_run-2_bold.nii.gz')
        f = File(path)
        assert os.path.exists(f.path)
        assert f.filename is not None
        assert os.path.isdir(f.dirname)
        assert f.entities == {}

    def test_matches(self, file):
        assert file._matches()
        assert file._matches(extensions='nii.gz')
        assert not file._matches(extensions=['.txt', '.rtf'])
        file.entities = {'task': 'rest', 'run': '2' }
        assert file._matches(entities={'task': 'rest', 'run': 2})
        assert not file._matches(entities={'task': 'rest', 'run': 4})

    def test_named_tuple(self, file):
        file.entities = {'attrA': 'apple', 'attrB': 'banana' }
        tup = file.as_named_tuple()
        assert(tup.filename == file.path)
        assert isinstance(tup, tuple)
        assert not hasattr(tup, 'task')
        assert tup.attrA == 'apple'
