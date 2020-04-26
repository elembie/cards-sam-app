import json
import decimal
import logging
from json import JSONEncoder
from dataclasses import asdict
from http import HTTPStatus as s

from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

from user_service.entities import User

from . import db

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

def get_user(user: User) -> dict:

    result = db.get_item(
        Key=user.get_key(),
    )

    found = 'Item' in result

    if not found:
        return make_response(s.NOT_FOUND, {'message': 'User does not exist'})

    return make_response(s.OK, User(**result['Item']).to_dict())


def create_user(user: User, body: dict) -> dict:

    if not body:
        return make_response(s.BAD_REQUEST, {'message': 'No data sent'})

    try:
        user_name = body['name']
    except KeyError:
        log.error('No user name found in create user post body')
        return make_response(400, {'message': 'Must provide user name when creating user'})

    user.name = user_name

    try:
        db.put_item(
            Item=asdict(user),
            ConditionExpression=Attr('pk').not_exists() & Attr('sk').not_exists()
        )
    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            raise
        return make_response(s.CONFLICT, {'message': 'User already exists'})

    return make_response(s.CREATED, user.to_dict())