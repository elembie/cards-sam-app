import os
import json
import logging
from typing import Any, List
from dataclasses import asdict, dataclass, field

import boto3
from boto3.exceptions import Boto3Error

from user_service.entities import User
from user_service.routes import (
    make_response,
    create_user,
    get_user
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

    log.info(event)

    try:
        user = get_user_from_claims(event) 
    except KeyError:
        return make_response(400, {'message': 'No user information in access token'})

    try: 

        path = event['path']
        method = event['httpMethod']
        body = json.loads(event['body']) if event['body'] else None

        routes: List[Route] = [
            Route(path='/user', method='GET', function=get_user, args=[user]),
            Route(path='/user', method='POST', function=create_user, args=[user, body]),
        ]

        route: Route = next(
                (r for r in routes if r.path == path and r.method == method),
                None
            )
        
        if not route:
            log.error(f'Unhandled request route: {path}, method: {method}')
            return make_response(400, {'message': 'Route or method not supported'})

        log.info(f'Handling route [{path}] metho [{method}] with function {route.function.__name__}')

        return route.function(*route.args, **route.kwargs)

    except Exception as e:

        log.error(f'Exception when processing request: {str(e)}')
        raise
        # return make_response(500, {'message': 'Internal server error'})