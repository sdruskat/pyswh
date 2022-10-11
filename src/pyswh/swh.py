from enum import Enum
import logging
import time

import requests
from requests import exceptions as request_exceptions

from pyswh.errors import SwhSaveError

API_ROOT_URL = 'https://archive.softwareheritage.org/api/1/'
API_ENDPOINT_SAVE = 'origin/save/'
API_URL_PATH = '/url/'
visit_type = 'git'  # TODO Add bzr, hg, svn

log = logging.getLogger(__name__)


class RequestMethod(Enum):
    POST = 'POST'
    GET = 'GET'


def _build_request_url(origin_url):
    return _prepare_url(API_ROOT_URL + API_ENDPOINT_SAVE + visit_type + API_URL_PATH + origin_url)


def _check_rate_limit():
    response = requests.get('https://archive.softwareheritage.org/api/1/ping/')
    if response.status_code == 429:
        log.info('Rate limit exceeded. Backing off.')
        _back_off(response)
        return

    if int(response.headers['X-RateLimit-Remaining']) > 0:
        return
    else:
        _back_off(response)


def _request(method: RequestMethod, origin_url: str, auth_token: str):
    _check_rate_limit()
    request_url = _build_request_url(origin_url)
    headers = {'Accept': 'application/json'}
    if auth_token:
        log.debug('Making authenticated requests (authorization token).')
        headers['Authorization'] = f'Bearer {auth_token}'
    else:
        log.debug('Making anonymous requests.')
    if method is RequestMethod.POST:
        return requests.post(request_url, headers=headers)
    elif method is RequestMethod.GET:
        return requests.get(request_url, headers=headers)


def _init_save(origin_url: str, auth_token: str) -> requests.Response:
    """Initializes the save action against the Software Heritage API."""
    try:
        return _request(RequestMethod.POST, origin_url, auth_token)
    except request_exceptions.ConnectionError:
        raise SwhSaveError('Could not connect to the Software Heritage API. Are you connected to the internet?')


def _check_save_progress(origin_url, auth_token, task_id: str):
    try:
        response = _request(RequestMethod.GET, origin_url, auth_token)
    except request_exceptions.ConnectionError:
        raise SwhSaveError('Could not connect to the Software Heritage API. Are you connected to the internet?')

    response_json = response.json()

    if type(response_json) == list:
        response_json = get_current_result(response_json, task_id)

    save_status = response_json['save_task_status']
    if save_status == 'failed':
        raise SwhSaveError(f'Saving "{origin_url}" has failed with visit status "{response_json["visit_status"]}"!'
                           f'\nFull response: {response.text}')
    elif save_status == 'succeeded':
        log.info(f'Saving {origin_url} has succeeded with visit status {response_json["visit_status"]}!')
    else:  # One of not created, not yet scheduled, scheduled
        log.info(f'The save task for {origin_url} is {save_status}. '
                 f'Waiting for 1 sec. before checking the status again.')
        time.sleep(1)
        _check_save_progress(origin_url, auth_token, task_id)


def get_current_result(response_json, task_id):
    """Returns the object with the provided task id from a list of objects."""
    for obj in response_json:
        if obj['loading_task_id'] == task_id:
            return obj
    # If we're still here, the task ID could not be found
    raise SwhSaveError(f'Failed to retrieve the save task for {response_json[0]["origin_url"]}.\n'
                       f'Full response: {response_json}')


def _check_status(response: requests.Response, auth_token: str, task_id: str):
    """Initializes the save action against the Software Heritage API."""

    # First, check the overall requests status (accepted, rejected, pending)
    response_json = response.json()
    if type(response_json) == list:
        response_json = get_current_result(response_json, task_id)
    origin_url = response_json['origin_url']
    request_status = response_json['save_request_status']
    if request_status == 'pending':
        # Wait
        log.info(f'The request to save {origin_url} is still pending. '
                 f'Waiting for 1 sec. before checking the status again.')
        time.sleep(1)
        retry_response = _request(RequestMethod.GET, origin_url, auth_token)
        _check_status(retry_response, auth_token, task_id)
    elif request_status == 'rejected':
        raise SwhSaveError(f'The request to save {origin_url} has been rejected:\n'
                           f'Notes: {response_json["note"]}\nFull response: {response.content}')

    # Request status is accepted, check for save progress
    _check_save_progress(origin_url, auth_token, task_id)


def _prepare_url(origin_url: str) -> str:
    """The origin URL for the save request to the Software Heritage Archive API needs to end with a slash.
    Therefore, if there is no slash at the end of the provided origin URL, add it.

    :return the origin URL ending with a slash"""
    if origin_url.endswith('/'):
        return origin_url
    else:
        return origin_url + '/'


def _back_off(response: requests.Response):
    reset_time = int(response.headers['X-RateLimit-Reset'])
    now_time = int(time.time())
    sleep_time = reset_time - now_time + 2
    log.info(f'Rate limit exceeded. Waiting {sleep_time} seconds before retrying.')
    time.sleep(sleep_time)  # Wait until the reset time, and an extra 2 seconds to be on the safe side.


def save(origin_url: str, post_only: bool, auth_token: str):
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
