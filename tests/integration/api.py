import sys
import logging

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

cognito = boto3.client('cognito-idp')
user_pool_id = 'ap-southeast-2_H9SN2bqby'
app_client_id = '7s15kdmtc3rp33tct70en9u7d0'

def create_user(username: str, password: str) -> None:
    
    log.info(f'Creating user {username} with password {password}')

    # initial sign up
    response = cognito.sign_up(
        ClientId=app_client_id,
        Username=username,
        Password=password,
        UserAttributes=[
            {
                'Name': 'email',
                'Value': username
            },
            {
                'Name': 'phone_number',
                'Value': '+61444444444'
            }
        ]
    )

    # then confirm signup
    response = cognito.admin_confirm_sign_up(
        UserPoolId=user_pool_id,
        Username=username
    )

    log.info(f'User created response {str(response)}')


def authenticate_and_get_token(username: str, password: str) -> str:

    log.info(f'Logging in for user {username}')

    response = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=app_client_id,
        AuthFlow='ADMIN_NO_SRP_AUTH',
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password
        }
    )

    log.info('Log in successful')

    return response['AuthenticationResult']['IdToken']


def delete_user(username: str) -> None:

    log.info(f'Deleting user {username}')

    response = cognito.admin_delete_user(
        UserPoolId=user_pool_id,
        Username=username
    )

    log.info(f'Delete user response {str(response)}')
