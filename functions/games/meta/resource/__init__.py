import os
import boto3

if 'ENV' not in os.environ:
    # running locally
    dynamo = boto3.resource('dynamodb', endpoint_url='http://localhost:8000/')
else:
    dynamo = boto3.resource('dynamodb')

table = os.environ.get('TABLE_NAME', 'cards-app-table')
db = dynamo.Table(table)