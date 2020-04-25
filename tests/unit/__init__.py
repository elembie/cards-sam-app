import os
import warnings
from unittest import TestCase

import os
from pathlib import Path

import boto3

class BaseTestCase(TestCase):

    def setUp(self):

        warnings.filterwarnings(action="ignore", message="unclosed", 
                         category=ResourceWarning)

        table_name = os.environ.get('TABLE_NAME', 'cards-app-table')

        resource = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
        client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")

        try:
            table = resource.Table(table_name)
            table.delete()
        except client.exceptions.ResourceNotFoundException:
            pass

        result = resource.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH' 
                },
                {
                    'AttributeName': 'sk',
                    'KeyType': 'RANGE' 
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sk',
                    'AttributeType': 'S'
                },

            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )

    def tearDown(self):
        try:
            table_name = os.environ.get('TABLE_NAME', 'cards-app-table')
            client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")
            resource = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
            table = resource.Table(table_name)
            table.delete()
        except client.exceptions.ResourceNotFoundException:
            pass

