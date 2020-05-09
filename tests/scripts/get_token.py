import boto3

cognito = boto3.client('cognito-idp')
user_pool_id = 'ap-southeast-2_H9SN2bqby'
app_client_id = '7s15kdmtc3rp33tct70en9u7d0'
username='lewbailey94@gmail.com'

response = cognito.admin_initiate_auth(
    UserPoolId=user_pool_id,
    ClientId=app_client_id,
    AuthFlow='ADMIN_NO_SRP_AUTH',
    AuthParameters={
        "USERNAME": username,
        "PASSWORD": 'cardstest2020'
    }
)

print(response['AuthenticationResult']['IdToken'])