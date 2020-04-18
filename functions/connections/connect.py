import json

def handle(event, context):
    
    print(event)
    
    connection_id = event["requestContext"].get("connectionId")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'connectionId': connection_id,
            'message': 'Connected to game'
        })
    }