import os
import boto3

dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")


table = dynamodb.create_table(
    TableName=os.environ['TABLE_NAME'],
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

print("Table status:", table.table_status)