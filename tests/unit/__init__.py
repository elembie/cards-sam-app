import os
import warnings
from copy import deepcopy
from unittest import TestCase

import os
from pathlib import Path

import boto3
import docker
from docker import DockerClient
from docker.models.containers import Container

class BaseTestCase(TestCase):

    @classmethod
    def replace_auth_attribute(cls, event: dict, attribute: str, value: str) -> dict:

        new = deepcopy(event)
        new['requestContext']['authorizer']['claims'][attribute] = value
        return new    

    @classmethod
    def replace_event_username(cls, event: dict, username: str)-> dict:

        return cls.replace_auth_attribute(
                event,
                'cognito:username',
                username
            )

    @classmethod
    def replace_query_params(cls, event: dict, param: str, value: str):

        new = deepcopy(event)
        new['queryStringParameters'][param] = value
        return new


    @classmethod
    def replace_request_context_param(cls, event: dict, param: str, value: str):

        new = deepcopy(event)
        new['requestContext'][param] = value
        return new


    @classmethod
    def replace_event_game_id(cls, event: dict, game_id: str) -> dict:

        new = deepcopy(event)
        new['pathParameters']['game_id'] = game_id
        return new

    
    @classmethod
    def make_user_key(cls, user_id: str):
        return {
            'pk': f'USER#{user_id}',
            'sk': f'ENTITY'
        }

    @classmethod
    def setUpClass(cls):

        cls.docker: DockerClient = docker.from_env()
        cls.dynamo_container: Container = cls.docker.containers.run(
            image='amazon/dynamodb-local',
            ports={
                '8000':'8000',
            },
            detach=True
        )

    @classmethod
    def tearDownClass(cls):
        
        cls.dynamo_container.stop()
        cls.dynamo_container.remove()


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

        self.db = resource.Table(table_name)

    def tearDown(self):
        try:
            table_name = os.environ.get('TABLE_NAME', 'cards-app-table')
            client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")
            resource = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
            table = resource.Table(table_name)
            table.delete()
        except client.exceptions.ResourceNotFoundException:
            pass

