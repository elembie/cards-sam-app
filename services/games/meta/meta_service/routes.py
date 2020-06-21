import re
import json
import decimal
import logging
from typing import Any
from json import JSONEncoder
from http import HTTPStatus as s
from dataclasses import asdict, dataclass

from boto3.exceptions import Boto3Error
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.types import TypeSerializer

from meta_service.entities import User, GameMeta, GameUser, GameTypesEnum

from . import db, table, db_client

log = logging.getLogger()
log.setLevel(logging.INFO)

serializer = TypeSerializer()

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


def as_dynamo_dict(data: dict) -> dict:
    return {
        k: serializer.serialize(v)
        for k, v in data.items()
    }



def create_game(user: User, body: dict):
    '''Create a new game and add the user to it'''

    if user.in_game:
        return make_response(s.CONFLICT, {'message': 'Cannot create game while currently playing'})

    log.info(f'Creating game with data {json.dumps(body)}')

    try:
        if body['game_type'] not in GameTypesEnum.to_list():
            return make_response(s.BAD_REQUEST, {'message': 'Invalid game type'})
    except KeyError:
        return make_response(s.BAD_REQUEST, {'message': 'No game type selected'})

    # if game attributes are missing use default
    try:
        game = GameMeta(created_by=user.id, **body)
    except TypeError as e:
        return make_response(s.BAD_REQUEST, {'message': f'Invalid key in create game data: {str(e)}'})

    try:
        db.put_item(
            Item=asdict(game)
        )
    except Boto3Error as e:
        log.error(f'Unable to create game due to exception: {str(e)}')
        raise

    response = enter_game(user, game.id)

    if response['statusCode'] != 200:
        log.error(f'Unable to set user {user.id} in game {game.id}')
        log.info('Rolling back game')
        db.delete_item(
            Key=game.get_key()
        )
        return response

    return make_response(s.CREATED, json.loads(response['body']))



def enter_game(user: User, game_id: str):

    if user.in_game:
        return make_response(s.CONFLICT, {'message': 'Cannot join a game while currently playing'})

    log.info(f'Adding user {user.id} to game {game_id}')

    try:
        response = db_client.transact_write_items(
            TransactItems=[
                {
                    'Update': {
                        'TableName': table,
                        'Key': as_dynamo_dict(GameMeta.make_key(game_id)),
                        'UpdateExpression': 'SET players_joined = players_joined + :p, players = list_append(players, :pid)',
                        'ConditionExpression': 'players_joined < table_size AND NOT contains(players, :pid)',
                        'ExpressionAttributeValues': {
                            ':p': { 'N': '1' },
                            ':pid': serializer.serialize([user.id])

                        },
                        'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                    }
                },
                {
                    'Update': {
                        'TableName': table,
                        'Key': as_dynamo_dict(user.get_key()),
                        'UpdateExpression': 'set in_game = :g, game_id = :gid',
                        'ExpressionAttributeValues': {
                            ':g': serializer.serialize(True),
                            ':gid': serializer.serialize(game_id)
                        },
                        'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                    }
                }
                
            ]
        )
    except db_client.exceptions.TransactionCanceledException:

        log.error(f'User {user.id} unable to join game {game_id}')

        try:
            game = db.get_item(Key=GameMeta.make_key(game_id))['Item']

            if game['players_joined'] == game['table_size']:
                return make_response(s.CONFLICT, {'message': 'Unable to join - game is full'})
            elif user.id in game['players']:
                # player already in game so OK
                return make_response(s.OK, GameMeta(**response['Item']).to_dict())
        except:
            pass

        return make_response(s.CONFLICT, {'message': 'Player unable to join'})


    response = db.get_item(
        Key=GameMeta.make_key(game_id)
    )

    if 'Item' not in response:
        return make_response(s.OK, {'message', 'User added but could not get game data'})

    return make_response(s.OK, GameMeta(**response['Item']).to_dict())


def exit_game(user: User, game_id: str):
    '''Removes a user from the game metadata'''

    if not user.in_game:
        return (s.CONFLICT, {'message': 'Cannot exit - not currently playing'})

    response = db.get_item(
        Key=GameMeta.make_key(game_id)
    )

    if 'Item' not in response:
        return make_response(s.NOT_FOUND, {'message', 'Could not find game meta'})

    game: GameMeta = GameMeta(**response['Item'])

    try:
        user_index = game.players.index(user.id)
    except ValueError:
        return make_response(s.CONFLICT, {'message': 'User not found in game'})
    
    try:
        response = db_client.transact_write_items(
            TransactItems=[
                {
                    'Update': {
                        'TableName': table,
                        'Key': as_dynamo_dict(GameMeta.make_key(game_id)),
                        'UpdateExpression': f'SET players_joined = players_joined - :p REMOVE players[{user_index}]',
                        'ConditionExpression': f'players[{user_index}] = :pid',
                        'ExpressionAttributeValues': {
                            ':p': { 'N': '1' },
                            ':pid': serializer.serialize(user.id),
                        },
                        'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                    }
                },
                {
                    'Update': {
                        'TableName': table,
                        'Key': as_dynamo_dict(user.get_key()),
                        'UpdateExpression': 'set in_game = :g, game_id = :gid',
                        'ExpressionAttributeValues': {
                            ':g': serializer.serialize(False),
                            ':gid': serializer.serialize(None)
                        },
                        'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                    }
                }
                
            ]
        )

    except db_client.exceptions.TransactionCanceledException as e:
        log.error(f'Could not remove user due to exception {e}')
        return make_response(s.INTERNAL_SERVER_ERROR, {'message': 'Could not remove user from game'}) 

    log.info(f'User {user.id} exited game {game_id}')
    return make_response(200)

