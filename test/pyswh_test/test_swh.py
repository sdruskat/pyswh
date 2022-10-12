# SPDX-FileCopyrightText: 2022 Stephan Druskat <pyswh@sdruskat.net>
#
# SPDX-License-Identifier: MIT
import time

import pytest
import responses
import requests

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


@responses.activate
def test_back_off():

    current_epoch = int(time.time())
    responses.add(responses.GET, 'https://my.api/api/1/foobar',
                  headers={'X-RateLimit-Reset': str(current_epoch + 5)},  # Rate limit will be "reset" in 2 secs.
                  status=200)
    response = requests.get('https://my.api/api/1/foobar')
    swh._back_off(response)
    assert int(time.time() - current_epoch) == 7  # 2 secs. added in MOT
