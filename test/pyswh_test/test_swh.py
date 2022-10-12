# SPDX-FileCopyrightText: 2022 Stephan Druskat <pyswh@sdruskat.net>
#
# SPDX-License-Identifier: MIT

import pytest

from pyswh import swh
# from pyswh.errors import SwhSaveError


@pytest.mark.parametrize('test_input, expected', [
    ('abc', 'abc/'),
    ('abc/', 'abc/'),
    ('https://www.domain.tld/dir', 'https://www.domain.tld/dir/'),
    ('https://www.domain.tld/dir/', 'https://www.domain.tld/dir/')
    ])
def test_prepare_url(test_input, expected):
    assert swh._prepare_url(test_input) == expected
