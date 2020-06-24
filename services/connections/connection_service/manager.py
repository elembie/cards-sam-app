import json
import decimal
import logging
from json import JSONEncoder

import boto3
from boto3.dynamodb.conditions import Key
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
                log.warn(f'Key {key} not present in record - skipped')
                continue
            keys[key] = serializer.deserialize(keys[key])

        if 'GAME#' in keys['pk'] and ('META' in keys['sk'] or 'STATE' in keys['sk']):

            game_id = keys.get('pk')[5:]
            game_image = { k: serializer.deserialize(v) for k,v in image.items() }

            log.info(f'Updating connections to game {game_id}')

            connections = db.query(
                KeyConditionExpression=Key('pk').eq(f'GAME#{game_id}') & Key('sk').begins_with('CONN#'),
            )['Items']

            log.info(f'Connections: {connections}')

            message = {
                'type': 'META_UPDATE',
                'data': game_image,
            }

            for conn in connections:
                log.info(f'Sending game update to user {conn["user_id"]} on connection ID {conn["connection_id"]}')

                try:
                    client.post_to_connection(
                        ConnectionId=conn['connection_id'],
                        Data=json.dumps(message, cls=DecimalEncoder).encode('utf-8')
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] == 'GoneException':
                        log.warn(f'Gone exception for {conn["connection_id"]}')
                    else:
                        raise

