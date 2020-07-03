import json
import decimal
import logging
from json import JSONEncoder
from http import HTTPStatus as s
from dataclasses import dataclass, asdict

from boto3.dynamodb.conditions import Key

from . import db

from shd_service.game import Game
from shd_service.exceptions import InvalidMessage


log = logging.getLogger()
log.setLevel(logging.INFO)

class DecimalEncoder(JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def make_response(code: int, body: dict = {}) -> dict:
    '''Generates HTTP response expected by API gateway'''

    return {
        'statusCode': code,
        'headers': {
                'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


class Actions:
    start_game = 'start_game'


@dataclass
class Action:

    game_id: str = None
    type: str = None
    data: dict = None

    @classmethod
    def from_message(cls, message: dict):

        game_id = message.get('gameId', None)
        action_type = message.get('type', None)
        data = message.get('data', None) 

        if not game_id:
            raise InvalidMessage('No game ID provided')
        elif not action_type:
            raise InvalidMessage('No action or type')
        
        return cls(
            game_id=game_id,
            type=action_type,
            data=data
        )


def handle(event, context):

    try:

        log.info(event)

        request_context = event.get('requestContext', None)
        body = json.loads(event.get('body', None))
        connection_id = request_context.get('connectionId', None)

        if not context or not body:
            return make_response(s.BAD_REQUEST, {'message', 'Cannot find context or message body'})
        elif not connection_id:
            return make_response(s.BAD_REQUEST, {'message', 'Cannot find connection ID'})

        action = None

        try:
            action = Action.from_message(body)
        except InvalidMessage as e:
            log.error(f'Unable to load action due to error {e}')
            return make_response(s.BAD_REQUEST, {'message': 'Invalid message schema'})

        log.info(f'Processing action: {asdict(action)}')

        game_entities = db.query(
            KeyConditionExpression=Key('pk').eq(f'GAME#{action.game_id}')
        ).get('Items', None)

        meta = None
        state = None
        player_conn = None
        player_id = None

        for entity in game_entities:
            sk = entity['sk']
            if 'CONN#' in sk and entity['connection_id'] == connection_id:
                player_conn = entity
                player_id = entity['user_id']
            elif sk == 'META':
                meta = entity
            elif sk == 'STATE':
                state = entity

        log.info(meta)
        log.info(state)
        log.info(player_conn)
            
        if action.type == Actions.start_game:
            
            if state:
                return make_response(s.CONFLICT, {'message', 'Cannot create - game already exists'})
            elif int(meta['table_size']) != len(meta['players']):
                return make_response(s.CONFLICT, {'message', 'Game not full, cannot start'})

        else:
            return make_response(s.BAD_REQUEST, {'message': 'Unknown action type'})

        return make_response(s.OK, {})

    except Exception as e:
        log.error('Error when processing websocket message: {e}')
        raise
        #return make_response(s.INTERNAL_SERVER_ERROR, {'message': 'Error when processing message'})