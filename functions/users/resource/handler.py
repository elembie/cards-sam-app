import os
import json
import logging
from dataclasses import asdict

import boto3
from boto3.exceptions import Boto3Error

try:
    from resource.entities import User
except ImportError:
    # unit testing import
    from functions.users.resource.entities import User


log = logging.getLogger()
log.setLevel(logging.INFO)


if 'ENV' not in os.environ:
    # running locally
    dynamo = boto3.resource('dynamodb', endpoint_url='http://localhost:8000/')
else:
    dynamo = boto3.resource('dynamodb')

table = dynamo.Table(os.environ.get('TABLE_NAME', 'cards-app-table'))


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


def get_or_create_user(user: User) -> dict:

    user_dict = asdict(user)   

    result = table.get_item(
        Key={
            'pk': user.pk,
            'sk': user.sk,
        }
    )

    found = 'Item' in result

    if found:
        return make_response(200, {'user': User(**result['Item']).to_dict()})
    else:
        log.info(f'User {user.id} not found in game table, creating new user')

    try:
        table.put_item(
            Item=user_dict
        )
    except Boto3Error as e:
        log.error(f'Unable to create user {user.id} due to exception: {str(e)}')
        raise

    return make_response(201, {'user': user.to_dict()})


def handle(event, context):

    log.info(event)
    try:
        user = get_user_from_claims(event) 
    except KeyError:
        return make_response(400, {'message': 'No user information in access token'})

    try: 

        path = event['path']
        method = event['httpMethod']

        routes = [
            {'path': '/user', 'method': 'GET', 'function': get_or_create_user, 'args': [user]},
        ]

        route = next(
                (r for r in routes if r['path'] == path and r['method'] == method),
                None
            )
        
        if not route:
            log.error(f'Unhandled request route: {path}, method: {method}')
            return make_response(400, {'message': 'Route or method not supported'})

        log.info(f'Handling route [{path}] metho [{method}] with function {route["function"].__name__}')
        return route['function'](*route['args'])

    except Exception as e:

        log.error(f'Exception when processing request: {str(e)}')
        return make_response(500, {'message': 'Internal server error'})