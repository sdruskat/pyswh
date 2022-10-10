import pytest

from pyswh import errors


@pytest.fixture()
def swh_save_error():
    return errors.SwhSaveError('I am an error.')


def test_swh_save_error(swh_save_error):
    assert type(swh_save_error) is errors.SwhSaveError
    assert type(swh_save_error) is not Exception
