import re
import json
import logging
from typing import Any
from dataclasses import asdict, dataclass

from boto3.exceptions import Boto3Error
from boto3.dynamodb.types import TypeSerializer

from service.entities import User, GameMeta, GameUser, GameTypesEnum

from . import db, table, db_client

log = logging.getLogger()
log.setLevel(logging.INFO)

serializer = TypeSerializer()


def make_response(code: int, body: dict = {}) -> dict:
    '''Generates HTTP response expected by API gateway'''

    return {
        'statusCode': code,
        'headers': {
                'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }


def get_user_key(user_id: str) -> dict:
    return {
        'pk': f'USER#{user_id}',
        'sk': f'#META#{user_id}'
    }


def as_dynamo_dict(data: dict) -> dict:
    return {
        k: serializer.serialize(v)
        for k, v in data.items()
    }



def create_game(user_id: str, in_game: bool, body: dict):
    '''Create a new game and add the user to it'''

    if in_game:
        return {403, {'message': 'Cannot create game while currently playing'}}

    log.info(f'Creating game with data {json.dumps(body)}')

    try:
        if body['game_type'] not in GameTypesEnum.to_list():
            return make_response(400, {'message': 'Invalid game type'})
    except KeyError:
        return make_response(400, {'message': 'No game type selected'})

    # if game attributes are missing use default
    try:
        game = GameMeta(created_by=user_id, **body)
    except TypeError as e:
        return make_response(400, {'message': f'Invalid key in create game data: {str(e)}'})

    try:
        db.put_item(
            Item=asdict(game)
        )
    except Boto3Error as e:
        log.error(f'Unable to create game due to exception: {str(e)}')
        raise

    response = enter_game(user_id, in_game, game.id)

    if response['statusCode'] != 200:
        log.error(f'Unable to set user {user_id} in game {game.id}')
        log.info('Rolling back game')
        db.delete_item(
            Key=game.get_key()
        )
        return response

    return make_response(201, response['body'])


def enter_game(user_id: str, in_game: bool, game_id: str):

    if in_game:
        return make_response(403, {'message': 'Cannot create game while currently playing'})

    log.info(f'Adding user {user_id} to game {game_id}')

    try:
        game_user = GameUser(user_id=user_id, game_id=game_id)
    except TypeError as e:
        log.error(f'Unable to create user game mapping for user {user_id} and game {game_id}: {str(e)}')
        return make_response(500, {'message': 'Unable to add user to game'})

    response = db_client.transact_write_items(
        TransactItems=[
            {
                'Put': {
                    'TableName': table,
                    'Item': game_user.to_dynamo(),
                    'ConditionExpression': 'attribute_not_exists(sk)',
                    'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                },
            },
            {
                'Update': {
                    'TableName': table,
                    'Key': as_dynamo_dict(GameMeta.make_key(game_id)),
                    'UpdateExpression': 'SET players_joined = players_joined + :p, players = list_append(players, :pid)',
                    'ConditionExpression': 'players_joined < table_size',
                    'ExpressionAttributeValues': {
                        ':p': { 'N': '1' },
                        ':pid': serializer.serialize([user_id])

                    },
                    'ReturnValuesOnConditionCheckFailure': 'ALL_OLD'
                }
            },
            {
                'Update': {
                    'TableName': table,
                    'Key': as_dynamo_dict(get_user_key(user_id)),
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

    response = db.get_item(
        Key=GameMeta.make_key(game_id)
    )

    if 'Item' not in response:
        return make_response(404, {'message', 'User added but could not get game data'})

    return make_response(200, GameMeta(**response['Item']).to_dict())


def exit_game(user_id: str, in_game: bool, game_id: str):
    '''Removes a user from the game metadata'''

    if not in_game:
        return (403, {'message': 'Cannot exit - not currently playing'})

    log.info('EXITING GAME')
    return make_response(200)
    # try:
    #     meta = db.get_item
    # except Boto3Error as e:
    #     log.error(f'Unable to find game meta data for game {game_id} due to exception: {str(e)}')
    #     return make_response(500, {'message': 'Unable to find game'})
