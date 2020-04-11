import json

def handle(event, context):

    print(event)

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({ 'message': 'Authenticated call!' })
    }