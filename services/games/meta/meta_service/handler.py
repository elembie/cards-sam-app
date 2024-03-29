import os
import re
import json
import logging
from typing import List, Any
from dataclasses import asdict, dataclass, field

import boto3
from boto3.exceptions import Boto3Error

from meta_service.entities import User
from meta_service.routes import (
    get_game,
    create_game,
    enter_game,
    exit_game,
    make_response,
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
    

guid = '[A-Za-z0-9-]+'


def handle(event, context):
    '''Lambda routing function to handle game metadata resource e.g.'''

    log.info(event)
        
    try: 

        try:
            user_id = event['requestContext']['authorizer']['claims']['cognito:username']
        except KeyError:
            return make_response(401, {'message': 'Unauthorised'})

        user = User(id=user_id)

        # initial validations
        result = db.get_item(
            Key=user.get_key()
        )

        if not 'Item' in result:
            return make_response(401, {'Message': 'Could not find user'})

        user.in_game = result['Item']['in_game']
        user.game_id = result['Item']['game_id']

        # route and process response
        path = event['path']
        method = event['httpMethod']
        body = json.loads(event['body']) if event['body'] else None

        game_id = None
        
        if event['pathParameters']:
            params = event['pathParameters']
            game_id = params['game_id'] if 'game_id' in params else None

        routes = [
            Route(path='/games', method='GET', function=get_game, args=[user]),
            Route(path='/games', method='POST', function=create_game, args=[user, body]),
            Route(path=f'/games/{guid}/players$', method='POST', function=enter_game, args=[user, game_id]),
            Route(path=f'/games/{guid}/players$', method='DELETE', function=exit_game, args=[user, game_id]),
        ]

        route = next(
                (r for r in routes if re.fullmatch(r.path, path) and r.method == method),
                None
            )
        
        if not route:
            log.error(f'Unhandled request route: {path}, method: {method}')
            return make_response(400, {'message': 'Route or method not supported'})

        log.info(f'Handling route [{path}] method [{method}] with function {route.function.__name__}')
        
        return route.function(*route.args, **route.kwargs)


    except Exception as e:

        log.error(f'Exception when processing request: {str(e)}')
        raise
        # return make_response(500, {'message': 'Internal server error'})