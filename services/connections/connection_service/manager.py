import logging

from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeDeserializer

from . import db, table, db_client

log = logging.getLogger()
log.setLevel(logging.INFO)

serializer = TypeDeserializer()

def process_stream(records: list):

    for record in records:

        keys: dict = record['dynamodb']['Keys']

        for key in ['sk', 'pk']:
            if not keys.get(key, None):
                log.warn(f'Key {key} not present in record - skipped')
                continue
            keys[key] = serializer.deserialize(keys[key])

        print(f'Processing record with keys {keys}')

        if 'GAME#' in keys['pk'] and ('META' in keys['sk'] or 'STATE' in keys['sk']):

            game_id = keys['pk'][5:]

            print(f'Updating connections to game {game_id}')

            connections = db.query(
                KeyConditionExpression=Key('pk').eq(f'GAME#{game_id}') & Key('sk').begins_with('CONN#'),
            )['Items']

            print(connections)

            pass
