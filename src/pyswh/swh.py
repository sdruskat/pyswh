# SPDX-FileCopyrightText: 2022 Stephan Druskat <pyswh@sdruskat.net>
#
# SPDX-License-Identifier: MIT

from enum import Enum
import logging
import time
import typing as t

import requests
from requests import exceptions as request_exceptions

from pyswh.errors import SwhSaveError

_API_ROOT_URL = 'https://archive.softwareheritage.org/api/1/'
_API_ENDPOINT_SAVE = 'origin/save/'
_API_URL_PATH = '/url/'
_visit_type = 'git'  # TODO Add bzr, hg, svn

_log = logging.getLogger(__name__)


class _RequestMethod(Enum):
    """
    An enum representing API request methods, such as `post` and `get`.
    """
    POST = 'POST'
    GET = 'GET'


def _build_request_url(origin_url: str) -> str:
    """
    Constructs a valid request URL to use with the Software Heritage API from its parts.

    :param str origin_url: The URL for the origin source code repository that should be saved.
    :return: A valid request URL
    :rtype: str
    """
    return _prepare_url(_API_ROOT_URL + _API_ENDPOINT_SAVE + _visit_type + _API_URL_PATH + origin_url)


def _check_rate_limit():
    """
    Pings the SWH API to receive a response with rate limit information in the header,
    and triggers a backoff if the rate limit is exceeded, or an HTTP status code 429 (Too many requests) is encountered.
    :return:
    """
    response = requests.get('https://archive.softwareheritage.org/api/1/ping/')
    if response.status_code == 429:
        _log.info('Rate limit exceeded. Backing off.')
        _back_off(response)
        return

    if int(response.headers['X-RateLimit-Remaining']) > 0:
        return
    else:
        _back_off(response)


def _request(method: _RequestMethod, origin_url: str, auth_token: str) -> requests.Response:
    """
    Makes a rate limit-safe request to the SWH API and returns the :py:class:`requests.Response`.

    :param _RequestMethod method: The request method to use for the request.
    :param str origin_url: The origin URL to use for construction of the request URL.
    :param str auth_token: An optional SWH auth token.
    :return: The response returned for the request.
    :rtype: requests.Response
    """
    _check_rate_limit()
    request_url = _build_request_url(origin_url)
    headers = {'Accept': 'application/json'}
    if auth_token:
        _log.debug('Making authenticated requests (authorization token).')
        headers['Authorization'] = f'Bearer {auth_token}'
    else:
        _log.debug('Making anonymous requests.')
    if method is _RequestMethod.POST:
        return requests.post(request_url, headers=headers)
    elif method is _RequestMethod.GET:
        return requests.get(request_url, headers=headers)


def _init_save(origin_url: str, auth_token: str) -> requests.Response:
    """
    Requests the initial save action in the Software Heritage API.

    :param str origin_url: The URL for the origin source code repository to save in the Software Heritage Archive.
    :param str auth_token: An optional SWH auth token.
    :return: The response returned for the request.
    :rtype: requests.Response
    :raises SwhSaveError: if no connection to the internet exists.
    """
    """"""
    try:
        return _request(_RequestMethod.POST, origin_url, auth_token)
    except request_exceptions.ConnectionError:
        raise SwhSaveError('Could not connect to the Software Heritage API. Are you connected to the internet?')


def _check_save_progress(origin_url: str, auth_token: str, task_id: str):
    """
    Checks on the progress of the save action, and reports its results.

    :param str origin_url: The URL for the origin source code repository to save in the Software Heritage Archive.
    :param str auth_token: An optional SWH auth token.
    :param str task_id: The task id of the save task, provided by the SWH API.
    :raises SwhSaveError: if no connection to the internet exists, or if the save action was unsuccessful.
    """
    try:
        response = _request(_RequestMethod.GET, origin_url, auth_token)
    except request_exceptions.ConnectionError:
        raise SwhSaveError('Could not connect to the Software Heritage API. Are you connected to the internet?')

    response_json = response.json()

    if type(response_json) == list:
        response_json = _get_current_result(response_json, task_id)

    save_status = response_json['save_task_status']
    if save_status == 'failed':
        raise SwhSaveError(f'Saving "{origin_url}" has failed with visit status "{response_json["visit_status"]}"!'
                           f'\nFull response: {response.text}')
    elif save_status == 'succeeded':
        _log.info(f'Saving {origin_url} has succeeded with visit status {response_json["visit_status"]}!')
    else:  # One of not created, not yet scheduled, scheduled
        _log.info(f'The save task for {origin_url} is {save_status}. '
                  f'Waiting for 1 sec. before checking the status again.')
        time.sleep(1)
        _check_save_progress(origin_url, auth_token, task_id)


def _get_current_result(response_json: t.Any, task_id: str):
    """
    Retrieves the current result from a list of save results that the SWH API returns when `get`ting the save action
    with the provided task id.

    :param t.Any response_json: A list of request results, i.e., JSON objects.
    :param str task_id: The identifier of the current save task.
    :return: The JSON response object for the current task id.
    :rtype: t.Any
    :raises SwhSaveError: if the response with the current task id cannot be found in the list of responses.
    """
    """Returns the object with the provided task id from a list of objects."""
    for obj in response_json:
        if obj['loading_task_id'] == task_id:
            return obj
    # If we're still here, the task ID could not be found
    raise SwhSaveError(f'Failed to retrieve the save task for {response_json[0]["origin_url"]}.\n'
                       f'Full response: {response_json}')


def _check_status(response: requests.Response, auth_token: str, task_id: str):
    """
    Checks the status of the save action as reported by the :py:class:`requests.Response`.

    :param requests.Response response: The response of the initial save request.
    :param str auth_token: An optional SWH auth token.
    :param str task_id: The task id of the current save task.
    :raises SwhSaveError: if the save request has been rejected.
    """

    # First, check the overall requests status (accepted, rejected, pending)
    response_json = response.json()
    if type(response_json) == list:
        response_json = _get_current_result(response_json, task_id)
    origin_url = response_json['origin_url']
    request_status = response_json['save_request_status']
    if request_status == 'pending':
        # Wait
        _log.info(f'The request to save {origin_url} is still pending. '
                  f'Waiting for 1 sec. before checking the status again.')
        time.sleep(1)
        retry_response = _request(_RequestMethod.GET, origin_url, auth_token)
        _check_status(retry_response, auth_token, task_id)
    elif request_status == 'rejected':
        raise SwhSaveError(f'The request to save {origin_url} has been rejected:\n'
                           f'Notes: {response_json["note"]}\nFull response: {response.content}')

    # Request status is accepted, check for save progress
    _check_save_progress(origin_url, auth_token, task_id)


def _prepare_url(origin_url: str) -> str:
    """
    Prepares the request URL for a request against the SWH API.

    The origin URL for the save request to the Software Heritage Archive API needs to end with a slash.
    Therefore, if there is no slash at the end of the provided origin URL, add it.

    :return the origin URL ending with a slash"""
    if origin_url.endswith('/'):
        return origin_url
    else:
        return origin_url + '/'


def _back_off(response: requests.Response):
    """
    Backs off from making further API calls for the amount of time that is the difference between
    the current epoch and the epoch when the rate limit will be reset.

    :param requests.Response response: The response from which to extract the rate limit reset time.
    """
    reset_time = int(response.headers['X-RateLimit-Reset'])
    now_time = int(time.time())
    sleep_time = reset_time - now_time + 2
    _log.info(f'Rate limit exceeded. Waiting {sleep_time} seconds before retrying.')
    time.sleep(sleep_time)  # Wait until the reset time, and an extra 2 seconds to be on the safe side.


def save(origin_url: str, post_only: bool, auth_token: str):
    """
    Attempts to save code in the Software Heritage Archive.

    This method wraps the `/api/1/origin/save/ <https://archive.softwareheritage.org/1/origin/save/doc/>`_ endpoint.

    :param str origin_url: The URL of the origin (source code repository) that should be saved in the archive.
    :param bool post_only: Whether the URL should simply be posted to the API and return,
        without checking for the success of the save operation.
    :param str auth_token: An optional Software Heritage API authentication token.
    :raises SwhSaveError: if an error occurred during the save task, or if the save task was unsuccessful.
    """
    if post_only:
        _init_save(origin_url, auth_token)
    else:
        init_response = _init_save(origin_url, auth_token)
        status = init_response.status_code
        if status == 200:
            # The API promises exactly one object as content of the POST response, so we can safely get the task ID
            task_id = init_response.json()['loading_task_id']
            _check_status(init_response, auth_token, task_id)
        elif status == 400:
            raise SwhSaveError(f'An invalid visit type or origin url has been provided.\n'
                               f'URL: {origin_url}\n'
                               f'{init_response.content}')
        elif status == 403:
            raise SwhSaveError(f'The provided origin url is blacklisted.'
                               f'\nURL: {origin_url}'
                               f'\n{init_response.content}')
        elif status == 404:
            raise SwhSaveError(f'No save requests have been found for a given origin.'
                               f'\nURL: {origin_url}'
                               f'\n{init_response.content}')
        elif status == 429:  # Too many requests
            _back_off(init_response)
            save(origin_url, False, auth_token)
        else:
            raise SwhSaveError(f'The status of the API response is unknown. '
                               f'Please open a new issue reporting this at TODO. '
                               f'Status code: {status}')
