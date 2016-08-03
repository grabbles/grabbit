import pytest

class TestPrototype(object):

    # def test_file(self):
    #     with pytest.raises(OSError):
    #         f = File('missing_file.txt')
    #     filename = join(dirname(__file__), 'prototype.py')
    #     f = File('prototype.py')
    #     assert f.name == 'prototype.py'
    #     assert f.entities == {}

    def test_full(self):
        struct = Structure('tests/specs/test.json', 'tests/data/7t_trt')
        pprint(struct.get('subject', filter={'subject': '[1234]', 'run': '-1'}))
