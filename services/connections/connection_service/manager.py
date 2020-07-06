import json
import decimal
import logging
from json import JSONEncoder

import boto3
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

from . import db, table, db_client

log = logging.getLogger()
log.setLevel(logging.INFO)

serializer = TypeDeserializer()

client = boto3.client('apigatewaymanagementapi', endpoint_url='https://jepc6bx2m7.execute-api.ap-southeast-2.amazonaws.com/dev')

class DecimalEncoder(JSONEncoder):
    def default(self, o): # pylint: disable=method-hidden
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def post_to_connection(connection_id: str, data: dict):

    try:
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data, cls=DecimalEncoder).encode('utf-8')
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'GoneException':
            log.warn(f'Gone exception for {connection_id}')
        else:
            raise


def process_stream(records: list):

    for record in records:

        dynamo = record.get('dynamodb', None)

        if not dynamo:
            log.warn('Could not find dynamo object in record')
            continue

        keys: dict = dynamo.get('Keys', None)
        image: dict = dynamo.get('NewImage', None)

        if not keys or not image:
            log.warn('Could not find keys and/or image in record')
            continue

        for key in ['sk', 'pk']:
            if not keys.get(key, None):
                log.warn(f'Key {key} not present in record')
            keys[key] = serializer.deserialize(keys[key])

        game_entity_update = 'GAME#' in keys['pk']

        meta_update = game_entity_update and 'META' in keys['sk']
        state_update = game_entity_update and 'SANITISED' in keys['sk']
        player_update = game_entity_update and 'PLAYER#' in keys['sk']

        if meta_update or state_update:

            game_id = keys.get('pk')[5:]
            game_image = { k: serializer.deserialize(v) for k,v in image.items() }

            update_type = 'meta_update' if meta_update else 'state_update'
            log.info(f'{update_type} info for connection to game {game_id}')

            connections = db.query(
                KeyConditionExpression=Key('pk').eq(f'GAME#{game_id}') & Key('sk').begins_with('CONN#'),
            )['Items']

            log.info(f'Connections: {connections}')

            message = {
                'type': update_type,
                'data': game_image,
            }

            for conn in connections:
                log.info(f'Sending game update to user {conn["user_id"]} on connection ID {conn["connection_id"]}')
                post_to_connection(conn['connection_id'], message)
                

        elif player_update:

            game_id = keys.get('pk')[5:]
            player_image = { k: serializer.deserialize(v) for k,v in image.items()}
            player_id = player_image['id']

            log.info(f'Updating player {player_id}')

            connections = db.query(
                KeyConditionExpression=Key('pk').eq(f'GAME#{game_id}') & Key('sk').begins_with('CONN#'),
                FilterExpression=Attr('user_id').eq(player_id)
            )['Items']

            if len(connections) != 1:
                log.warn(f'Could not find connection to game {game_id} for player {player_id}')
                continue

            message = {
                'type': 'player_update',
                'data': player_image,
            }
            
            post_to_connection(connections[0]['connection_id'], message)







