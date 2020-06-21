import json
import time
import logging
from dataclasses import asdict
from http import HTTPStatus as s

from jose import JWTError
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

from connection_service.token import validate_and_decode

from . import db
from connection_service.entities import UserGameConnection

log = logging.getLogger()
log.setLevel(logging.INFO)

def make_response(code: s, body: dict = {}) -> dict:
    '''Generates HTTP response expected by API gateway'''

    return {
        'statusCode': code,
        'headers': {
                'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }


def validation_failed_response():
    return make_response(s.UNAUTHORIZED, {'message': 'Token validation failed'})


def handle(event, context):

    log.info(event)

    connection_id = event["requestContext"].get("connectionId", None)
    token = event.get("queryStringParameters", {}).get("token", None)

    if not connection_id:
        log.error(f'No connection ID provided')
        return make_response(s.BAD_REQUEST, {'message': 'No connection ID provided'})

    if event["requestContext"]["eventType"] == "CONNECT":

        if not token:
            log.error('Could not connect - no token present in connection request query string')
            return make_response(s.UNAUTHORIZED, {'message': 'No token provided when connecting'})

        log.info('Validating token and retrieving user')

        try:
            claims = validate_and_decode(token)
        except JWTError:
            return validation_failed_response()

        if not claims:
            return validation_failed_response()

        log.info(f'Token valid - claims: {claims}')

        user_id = claims.get('sub', None)

        if not user_id:
            log.error('Could not get user ID from claims')
            return validation_failed_response()

        user = db.get_item(
            Key={
                'pk': f'USER#{user_id}',
                'sk': f'ENTITY'
            }
        ).get('Item', None)

        if not user:
            return make_response(s.NOT_FOUND, {'message': 'Could not find user'})

        if not user.get('in_game', False) or not user.get('game_id', False):
            return make_response(s.CONFLICT, {'message', 'Cannot connect socket - user not in game'})

        log.info('Checking for existing connections')

        stale_connections = db.query(
            KeyConditionExpression=Key('pk').eq(f'GAME#{user["game_id"]}') & Key('sk').begins_with('CONN#'),
            FilterExpression=Attr('user_id').eq(user_id)
        )['Items']

        for conn in stale_connections:
            db.delete_item(Key={'pk': conn['pk'], 'sk': conn['sk']})

        log.info(f'Removed {len(stale_connections)} connections')

        log.info(f'Connecting user {user_id} to game {user["game_id"]} with connection ID {connection_id}')

        game_connection = UserGameConnection(
            connection_id=connection_id,
            game_id=user['game_id'],
            user_id=user_id,
            connected_at=int(time.time()),
        )

        log.info(f'Game connection {asdict(game_connection)}')

        try:
            response = db.put_item(
                Item=asdict(game_connection),
                ConditionExpression='attribute_not_exists(pk) AND attribute_not_exists(sk)'
            )
        except ClientError as e:
            log.error(f'Exception raised when storing connection: {e}')
            return make_response(s.INTERNAL_SERVER_ERROR, {'message': 'Error when saving connection'})

        log.info(response)

        return make_response(s.OK, {'message': 'Connected'})

    elif event["requestContext"]["eventType"] == "DISCONNECT":

        log.info(f'Disconnecting client ID {connection_id}')
        return make_response(200, {'message': 'Disconnected'})

    

    