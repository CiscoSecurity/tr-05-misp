from urllib.error import URLError

import jwt
from api.errors import AuthorizationError, InvalidArgumentError
from flask import request, jsonify, current_app
from jwt import (
    PyJWKClient, InvalidSignatureError, InvalidAudienceError,
    DecodeError, PyJWKClientError
)

NO_AUTH_HEADER = 'Authorization header is missing'
WRONG_AUTH_TYPE = 'Wrong authorization type'
WRONG_PAYLOAD_STRUCTURE = 'Wrong JWT payload structure'
WRONG_JWT_STRUCTURE = 'Wrong JWT structure'
WRONG_AUDIENCE = 'Wrong configuration-token-audience'
KID_NOT_FOUND = 'kid from JWT header not found in API response'
WRONG_KEY = ('Failed to decode JWT with provided key. '
             'Make sure domain in custom_jwks_host '
             'corresponds to your SecureX instance region.')
JWKS_HOST_MISSING = ('jwks_host is missing in JWT payload. Make sure '
                     'custom_jwks_host field is present in module_type')
WRONG_JWKS_HOST = ('Wrong jwks_host in JWT payload. Make sure domain follows '
                   'the visibility.<region>.cisco.com structure')


def get_auth_token():
    """
    Parse and validate incoming request Authorization header.
    """
    expected_errors = {
        KeyError: NO_AUTH_HEADER,
        AssertionError: WRONG_AUTH_TYPE
    }
    try:
        scheme, token = request.headers['Authorization'].split()
        assert scheme.lower() == 'bearer'
        return token
    except tuple(expected_errors) as error:
        raise AuthorizationError(expected_errors[error.__class__])


def get_key():
    """
    Get Authorization token and validate its signature
    against the public key from /.well-known/jwks endpoint.
    """
    expected_errors = {
        KeyError: WRONG_PAYLOAD_STRUCTURE,
        AssertionError: JWKS_HOST_MISSING,
        InvalidSignatureError: WRONG_KEY,
        DecodeError: WRONG_JWT_STRUCTURE,
        InvalidAudienceError: WRONG_AUDIENCE,
        PyJWKClientError: KID_NOT_FOUND,
        URLError: WRONG_JWKS_HOST
    }

    try:
        token = get_auth_token()
        jwks_host = jwt.decode(
            token, options={'verify_signature': False}
        ).get('jwks_host')
        assert jwks_host

        jwks_client = PyJWKClient(f'https://{jwks_host}/.well-known/jwks')
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        aud = request.url_root
        payload = jwt.decode(
            token, signing_key.key,
            algorithms=['RS256'], audience=[aud.rstrip('/')]
        )
        current_app.config['HOST'] = payload['HOST']

        return payload['AuthKey']
    except tuple(expected_errors) as error:
        raise AuthorizationError(expected_errors[error.__class__])


def get_json(schema):
    """
    Parse the incoming request's data as JSON.
    Validate it against the specified schema.
    """

    data = request.get_json(force=True, silent=True, cache=False)

    message = schema.validate(data)

    if message:
        raise InvalidArgumentError(message)

    return data


def jsonify_data(data):
    return jsonify({'data': data})


def jsonify_errors(data):
    return jsonify({'errors': [data]})