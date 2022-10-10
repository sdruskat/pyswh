import pytest

from pyswh import errors


@pytest.fixture()
def swh_save_error():
    return errors.SwhSaveError('I am an error.')


# noinspection PyPep8Naming
def test_SwhSaveError(swh_save_error):
    assert type(swh_save_error) is errors.SwhSaveError
    assert type(swh_save_error) is not Exception
