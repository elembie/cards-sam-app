import os
from unittest import TestCase

import os
from pathlib import Path

import boto3

class BaseTestCase(TestCase):

    def setUp(self):

        self.base_path = Path(os.getcwd())

        print(f'Base path for package {self.base_path}')

        table_name = os.environ.get('TABLE_NAME', 'cards-app-table')

        dynamo = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

        print(f'Creating table {table_name}')

        result = dynamo.create_table(
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

        self.db = dynamo.Table(table_name)

        print('Table created')

    def test_demo(self):
        print('Testing')

    def tearDown(self):
        print('Deleting table')
        self.db.delete()
        print('Table deleted')
