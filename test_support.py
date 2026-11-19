"""Helpers for the project’s Flask test-client scripts."""

import re


def get_csrf_token(client, path='/'):
    response = client.get(path)
    if response.status_code != 200:
        raise AssertionError(f'Could not load CSRF token page {path}: {response.status_code}')
    match = re.search(rb'<meta name="csrf-token" content="([^"]+)">', response.data)
    if not match:
        raise AssertionError(f'CSRF token missing from {path}')
    return match.group(1).decode()


def login(client, identifier, password, role, follow_redirects=True):
    response = client.get('/login')
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    if not match:
        raise AssertionError('Login CSRF token missing')
    return client.post('/login', data={
        'csrf_token': match.group(1).decode(),
        'identifier': identifier,
        'password': password,
        'role': role
    }, follow_redirects=follow_redirects)


def post_form(client, path, data=None, follow_redirects=True):
    payload = dict(data or {})
    payload['csrf_token'] = get_csrf_token(client)
    return client.post(path, data=payload, follow_redirects=follow_redirects)


def post_json(client, path, payload):
    return client.post(path, json=payload, headers={'X-CSRF-Token': get_csrf_token(client)})


def logout(client):
    return post_form(client, '/logout', follow_redirects=True)
