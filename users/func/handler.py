import json
import logging
from dataclasses import asdict

log = logging.getLogger()
log.setLevel(logging.INFO)

try:
    from func.lib.entities import User
except ImportError:
    # unit testing import
    from users.func.lib.entities import User


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
    

def handle(event, context):

    try: 

        user = get_user_from_claims(event)
        print(user)

        return make_response(200, {'user': asdict(user)})

    except Exception as e:

        log.warn(f'Exception when processing request: {str(e)}')
        return make_response(500, {'message': 'Internal server error'})