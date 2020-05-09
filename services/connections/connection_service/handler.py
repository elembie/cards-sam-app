import json
import logging
from http import HTTPStatus as s

from jose import JWTError

from connection_service.token import validate_and_decode

log = logging.getLogger()
log.setLevel(logging.INFO)

def make_response(code: int, body: dict = {}) -> dict:
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
    game_id = event.get("queryStringParameters", {}).get("gameId", None) 

    if not connection_id:
        log.error(f'No connection ID provided')
        return make_response(s.BAD_REQUEST, {'message': 'No connection ID provided'})

    if event["requestContext"]["eventType"] == "CONNECT":

        if not token:
            log.error('Could not connect - no token present in connection request query string')
            return make_response(s.UNAUTHORIZED, {'message': 'No token provided when connecting'})

        elif not game_id:
            log.error('Could not connect - no game ID in request query parameters')
            return make_response(s.BAD_REQUEST, {'message': 'No game ID provided'})

        log.info(f'Connecting client ID {connection_id} and token {token} to game {game_id}')

        try:
            claims = validate_and_decode(token)
        except JWTError:
            return validation_failed_response()

        if not claims:
            return validation_failed_response()

        log.info(f'Token valid - claims: {claims}')

        return make_response(200, {'message': 'Connected'})

    elif event["requestContext"]["eventType"] == "DISCONNECT":

        log.info(f'Disconnecting client ID {connection_id}')

        return make_response(200, {'message': 'Disconnected'})

    

    