# SPDX-FileCopyrightText: 2022 Stephan Druskat <pyswh@sdruskat.net>
#
# SPDX-License-Identifier: MIT
import time
import logging

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
    responses.get('https://my.api/api/1/foobar',
                  headers={'X-RateLimit-Reset': str(current_epoch)},  # Rate limit will be "reset" in 2 secs.
                  status=200)
    response = requests.get('https://my.api/api/1/foobar')
    swh._back_off(response)
    assert int(time.time() - current_epoch) == 2  # 2 secs. added in MOT


@responses.activate
def test_check_rate_limit_pass(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    with caplog.at_level(logging.DEBUG):
        swh._check_rate_limit()
    assert len(caplog.records) == 0


@responses.activate
def test_check_rate_limit_429(caplog):
    current_epoch = int(time.time())
    responses.get('https://archive.softwareheritage.org/api/1/ping/', status=429,
                  headers={'X-RateLimit-Reset': str(current_epoch)})
    with caplog.at_level(logging.DEBUG):
        swh._check_rate_limit()
    assert int(time.time() - current_epoch) == 2  # 2 secs. added in MOT
    assert caplog.records[0].msg == 'Too many requests! Backing off.'
    assert 'Rate limit exceeded' in caplog.records[1].msg


@responses.activate
def test_check_rate_limit_rate_limit(caplog):
    current_epoch = int(time.time())
    responses.get('https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(0),
                           'X-RateLimit-Reset': str(current_epoch)})
    with caplog.at_level(logging.DEBUG):
        swh._check_rate_limit()
    assert int(time.time() - current_epoch) == 2  # 2 secs. added in MOT
    assert caplog.records[0].msg == 'Rate limit exceeded. Backing off.'
    assert 'Rate limit exceeded' in caplog.records[1].msg


def test_build_request_url():
    assert swh._build_request_url('MOCK') == MOCK_SAVE_URL


@responses.activate
def test_request():
    responses.get('https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    responses.get(MOCK_SAVE_URL,
                  body='{"method": "GET"}', status=200,
                  content_type='application/json')
    responses.post(MOCK_SAVE_URL,
                   body='{"method": "POST"}', status=200,
                   content_type='application/json')

    assert swh._request(swh._RequestMethod.POST, 'MOCK', None).content == b'{"method": "POST"}'
    assert swh._request(swh._RequestMethod.GET, 'MOCK', None).content == b'{"method": "GET"}'


@responses.activate
def test_init_save_pass():
    responses.get('https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL,
                   body='{"method": "POST"}', status=200,
                   content_type='application/json')
    assert swh._init_save('MOCK', None).content == b'{"method": "POST"}'


@responses.activate
def test_init_save_raise():
    with pytest.raises(swh.SwhSaveError,
                       match='Could not connect to the Software Heritage API. Are you connected to the internet?'):
        swh._init_save('MOCK', None)


@responses.activate
def test_check_save_progress_raise_connection():
    with pytest.raises(swh.SwhSaveError,
                       match='Could not connect to the Software Heritage API during progress check. '
                             'Are you connected to the internet?'):
        swh._check_save_progress('MOCK', None, '123')


@responses.activate
def test_check_save_progress_succeed(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    responses.get(MOCK_SAVE_URL,
                  headers={'X-RateLimit-Remaining': str(1)},
                  body='[{"loading_task_id": "123", "save_task_status": "succeeded", "visit_status": "full"}]',
                  status=200)
    with caplog.at_level(logging.DEBUG):
        swh._check_save_progress('MOCK', None, '123')
    assert caplog.records[1].msg == 'Saving MOCK has succeeded with visit status full!'


@responses.activate
def test_check_save_progress_fail(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/',
                  headers={'X-RateLimit-Remaining': str(1)})
    responses.get(MOCK_SAVE_URL,
                  headers={'X-RateLimit-Remaining': str(1)},
                  body='[{"loading_task_id": "123", "save_task_status": "failed", "visit_status": "full"}]',
                  status=200)
    with pytest.raises(swh.SwhSaveError,
                       match='Saving "MOCK" has failed with visit status "full"!'):
        swh._check_save_progress('MOCK', None, '123')


@responses.activate
def test_check_save_progress_wait(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.get(MOCK_SAVE_URL,
                  headers={'X-RateLimit-Remaining': str(1)},
                  body='[{"loading_task_id": "123", "save_task_status": "pending", "visit_status": "full"}]',
                  status=200)
    responses.get(MOCK_SAVE_URL,
                  headers={'X-RateLimit-Remaining': str(1)},
                  body='[{"loading_task_id": "123", "save_task_status": "succeeded", "visit_status": "full"}]',
                  status=200)
    with caplog.at_level(logging.DEBUG):
        swh._check_save_progress('MOCK', None, '123')
    assert caplog.records[1].msg == 'The save task for MOCK is pending. ' \
                                    'Waiting for 1 sec. before checking the status again.'
    assert caplog.records[3].msg == 'Saving MOCK has succeeded with visit status full!'


@responses.activate
def test_save_post_only():
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL,
                   headers={'X-RateLimit-Remaining': str(1)},
                   body='{"loading_task_id": "123", "save_task_status": "succeeded", "visit_status": "full"}',
                   status=200)
    swh.save('MOCK', True, None)


@responses.activate
def test_save_400():
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL, status=400, body=b'NO_URL')
    with pytest.raises(swh.SwhSaveError,
                       match=f'An invalid visit type or origin url has been provided.\n'
                             f'URL: MOCK\n{str(b"NO_URL")}'):
        swh.save('MOCK', False, None)


@responses.activate
def test_save_403():
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL, status=403, body=b'BLACKLISTED')
    with pytest.raises(swh.SwhSaveError,
                       match=f'The provided origin url is blacklisted.\nURL: MOCK\n{str(b"BLACKLISTED")}'):
        swh.save('MOCK', False, None)


@responses.activate
def test_save_404():
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL, status=404, body=b'NOT FOUND')
    with pytest.raises(swh.SwhSaveError,
                       match=f'No save requests have been found for a given origin.\nURL: MOCK\n{str(b"NOT FOUND")}'):
        swh.save('MOCK', False, None)


@responses.activate
def test_save_429(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL,
                   status=429,
                   headers={'X-RateLimit-Reset': str(int(time.time()) + 1)})
    responses.post(MOCK_SAVE_URL,
                   headers={'X-RateLimit-Remaining': str(1)},
                   body='{"loading_task_id": "123", "save_task_status": "succeeded", "visit_status": "full",'
                        '"origin_url": "MOCK", "save_request_status": "accepted"}',
                   status=200)
    responses.get(MOCK_SAVE_URL,
                  headers={'X-RateLimit-Remaining': str(1)},
                  body='{"loading_task_id": "123", "save_task_status": "succeeded", "visit_status": "full",'
                       '"origin_url": "MOCK", "save_request_status": "accepted"}',
                  status=200)
    with caplog.at_level(logging.DEBUG):
        swh.save('MOCK', False, None)
    assert caplog.records[1].msg == 'Rate limit exceeded. Waiting 3 seconds before retrying.'
    assert caplog.records[4].msg == 'Saving MOCK has succeeded with visit status full!'


@responses.activate
def test_save_unknown_status(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL, status=410, body=b'GONE')
    with pytest.raises(swh.SwhSaveError,
                       match='The status of the API response is unknown. '
                             'Please open a new issue reporting this at https://github.com/sdruskat/pyswh/issues. '
                             'Status code: 410'):
        swh.save('MOCK', False, None)


@responses.activate
def test_save_succeed(caplog):
    responses.get('https://archive.softwareheritage.org/api/1/ping/', headers={'X-RateLimit-Remaining': str(1)})
    responses.post(MOCK_SAVE_URL,
                   headers={'X-RateLimit-Remaining': str(1)},
                   body='{"loading_task_id": "123", "save_task_status": "pending", "visit_status": "full", '
                        '"origin_url": "MOCK", "save_request_status": "pending"}',
                   status=200)
    responses.get(MOCK_SAVE_URL,
                  headers={'X-RateLimit-Remaining': str(1)},
                  body='[{"loading_task_id": "123", "save_task_status": "succeeded", "visit_status": "full",'
                       '"origin_url": "MOCK", "save_request_status": "accepted"}]',
                  status=200)
    with caplog.at_level(logging.DEBUG):
        swh.save('MOCK', False, None)
    assert caplog.records[1].msg == 'The request to save MOCK is still pending. ' \
                                    'Waiting for 1 sec. before checking the status again.'
    assert caplog.records[4].msg == 'Saving MOCK has succeeded with visit status full!'
    assert caplog.records[6].msg == 'Saving MOCK has succeeded with visit status full!'
