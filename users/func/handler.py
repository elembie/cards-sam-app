import json
import logging
from dataclasses import asdict

try:
    from func.lib.entities import User
except ImportError:
    # unit testing import
    from users.func.lib.entities import User


log = logging.getLogger()
log.setLevel(logging.INFO)


def make_response(code: int, body: dict) -> dict:

    return {
        'statusCode': code,
        'headers': {
                'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }


def get_user_from_claims(event: dict) -> User:

    claims = event['requestContext']['authorizer']['claims']

    return User(
        id = claims['cognito:username'],
        email = claims['email'],
        phone = claims['phone_number'],
    )


def get_or_create_user(event):

    user = get_user_from_claims(event)    


def handle(event, context):

    try: 

        path = event['path']
        method = event['httpMethod']

        routes = [
            {'path': '/user', 'method': 'GET', 'function': get_or_create_user},
        ]

        f = next(
                (r['function'] for r in routes if r['path'] == path and r['method'] == method),
                None
            )
        
        if not f:
            log.warn(f'Unhandled request route: {path}, method: {method}')
            return make_response(400, {'message': 'Route or method not supported'})

        return f(event)

    except Exception as e:

        log.warn(f'Exception when processing request: {str(e)}')
        return make_response(500, {'message': 'Internal server error'})