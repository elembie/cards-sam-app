import os
import re
import json
import logging
from typing import Any, List
from http import HTTPStatus as s
from dataclasses import asdict, dataclass, field

import boto3
from boto3.exceptions import Boto3Error

from user_service.entities import User
from user_service.routes import (
    make_response,
    create_user,
    get_user,
    get_player,
)

from . import db

log = logging.getLogger()
log.setLevel(logging.INFO)


@dataclass
class Route():
    path: str = None
    method: str = None
    function: Any = None
    args: List[Any] = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)


def get_user_from_claims(event: dict) -> User:

    claims = event['requestContext']['authorizer']['claims']

    return User(
        id = claims['cognito:username'],
        email = claims['email'],
        phone = claims['phone_number'],
    )


def handle(event, context):

    guid = '[A-Za-z0-9-]+'

    log.info(event)

    try:
        user = get_user_from_claims(event) 
    except KeyError:
        return make_response(s.UNAUTHORIZED, {'message': 'No user information in access token'})

    player_id = None
    if event['pathParameters']:
        params = event['pathParameters']
        player_id = params.get('player_id', None)

    try: 

        path = event['path']
        method = event['httpMethod']
        body = json.loads(event['body']) if event['body'] else None

        routes: List[Route] = [
            Route(path='/user', method='GET', function=get_user, args=[user]),
            Route(path=f'/user/{guid}', method='GET', function=get_player, args=[player_id]),
            Route(path='/user', method='POST', function=create_user, args=[user, body]),
        ]

        route = next(
            (r for r in routes if re.fullmatch(r.path, path) and r.method == method),
            None
        )
    
        if not route:
            log.error(f'Unhandled request route: {path}, method: {method}')
            return make_response(s.BAD_REQUEST, {'message': 'Route or method not supported'})

        log.info(f'Handling route [{path}] metho [{method}] with function {route.function.__name__}')

        return route.function(*route.args, **route.kwargs)

    except Exception as e:

        log.error(f'Exception when processing request: {str(e)}')
        raise
        # return make_response(500, {'message': 'Internal server error'})