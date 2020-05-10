import os
import boto3

if 'ENV' not in os.environ:
    # running locally
    db_resource = boto3.resource('dynamodb', endpoint_url='http://localhost:8000/')
    db_client = boto3.client('dynamodb', endpoint_url='http://localhost:8000/')
else:
    db_resource = boto3.resource('dynamodb')
    db_client = boto3.client('dynamodb')

table = os.environ.get('TABLE_NAME', 'cards-app-table')
db = db_resource.Table(table)