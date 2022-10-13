# SPDX-FileCopyrightText: 2022 Stephan Druskat <pyswh@sdruskat.net>
#
# SPDX-License-Identifier: MIT
import time

import pytest
import responses
import requests

from pyswh import swh
# from pyswh.errors import SwhSaveError


MOCK_SAVE_URL = 'https://archive.softwareheritage.org/api/1/origin/save/git/url/MOCK/'


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
                  headers={'X-RateLimit-Reset': str(current_epoch)},  # Rate limit will be "reset" in 2 secs.
                  status=200)
    response = requests.get('https://my.api/api/1/foobar')
    swh._back_off(response)
    assert int(time.time() - current_epoch) == 2  # 2 secs. added in MOT


@responses.activate
def test_check_rate_limit_pass(caplog):
    responses.add(responses.GET, 'https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    swh._check_rate_limit()
    assert not caplog.text


@responses.activate
def test_check_rate_limit_429(caplog):
    current_epoch = int(time.time())
    responses.add(responses.GET, 'https://archive.softwareheritage.org/api/1/ping/', status=429,
                  headers={'X-RateLimit-Reset': str(current_epoch)})
    swh._check_rate_limit()
    assert int(time.time() - current_epoch) == 2  # 2 secs. added in MOT


@responses.activate
def test_check_rate_limit_rate_limit(caplog):
    current_epoch = int(time.time())
    responses.add(responses.GET, 'https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(0),
                           'X-RateLimit-Reset': str(current_epoch)})
    swh._check_rate_limit()
    assert int(time.time() - current_epoch) == 2  # 2 secs. added in MOT


def test_build_request_url():
    assert swh._build_request_url('MOCK') == MOCK_SAVE_URL


@responses.activate
def test_request():
    responses.add(responses.GET, 'https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    responses.add(responses.GET, MOCK_SAVE_URL,
                  body='{"method": "GET"}', status=200,
                  content_type='application/json')
    responses.add(responses.POST, MOCK_SAVE_URL,
                  body='{"method": "POST"}', status=200,
                  content_type='application/json')

    assert swh._request(swh._RequestMethod.POST, 'MOCK', None).content == b'{"method": "POST"}'
    assert swh._request(swh._RequestMethod.GET, 'MOCK', None).content == b'{"method": "GET"}'


@responses.activate
def test_init_save_pass():
    responses.add(responses.GET, 'https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    responses.add(responses.POST, MOCK_SAVE_URL,
                  body='{"method": "POST"}', status=200,
                  content_type='application/json')
    assert swh._init_save('MOCK', None).content == b'{"method": "POST"}'


@responses.activate
def test_init_save_raise():
    with pytest.raises(swh.SwhSaveError,
                       match='Could not connect to the Software Heritage API. Are you connected to the internet?'):
        swh._init_save('MOCK', None)


@responses.activate
def test_check_save_progress():
    with pytest.raises(swh.SwhSaveError,
                       match='Could not connect to the Software Heritage API during progress check. '
                             'Are you connected to the internet?'):
        swh._check_save_progress('MOCK', None, '123')

    # response_json = response.json()
    #
    # if type(response_json) == list:
    #     response_json = _get_current_result(response_json, task_id)
    #
    # save_status = response_json['save_task_status']
    # if save_status == 'failed':
    #     raise SwhSaveError(f'Saving "{origin_url}" has failed with visit status "{response_json["visit_status"]}"!'
    #                        f'\nFull response: {response.text}')
    # elif save_status == 'succeeded':
    #     _log.info(f'Saving {origin_url} has succeeded with visit status {response_json["visit_status"]}!')
    # else:  # One of not created, not yet scheduled, scheduled
    #     _log.info(f'The save task for {origin_url} is {save_status}. '
    #               f'Waiting for 1 sec. before checking the status again.')
    #     time.sleep(1)
    #     _check_save_progress(origin_url, auth_token, task_id)
