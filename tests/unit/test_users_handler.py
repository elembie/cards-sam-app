import os
import sys
import json
import uuid
from pathlib import Path
from copy import deepcopy
from http import HTTPStatus as s

from . import BaseTestCase
from unittest.mock import patch, MagicMock

sys.dont_write_bytecode = True

test_path = str(Path(os.getcwd()) / 'services' / 'users')
sys.path.append(test_path)

from services.users.user_service.entities import User
from services.users.user_service.handler import handle, get_user_from_claims


class TestUserHanlder(BaseTestCase):

    def setUp(self):

        super().setUp()

        with open('tests/events/create-user-authd.json', 'r') as f:
            self.create_user_authd_event = json.load(f)   

        with open('tests/events/get-user-authd.json', 'r') as f:
            self.get_user_authd_event = json.load(f)   

        with open('tests/events/get-user-no-claims.json', 'r') as f:
            self.get_user_no_claims_event = json.load(f)   

        with open('tests/events/get-player-authd.json', 'r') as f:
            self.get_player_authd_event = json.load(f)  
            
             
    def test_get_user_from_event_clams(self):

        user = get_user_from_claims(self.get_user_authd_event)
        self.assertEqual(user.id, '04f19018-c27e-4097-b84c-49ed474d0134')
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(user.phone, '+61999999999')


    def test_create_user(self):

        response = handle(self.create_user_authd_event, None)

        result = json.loads(response['body'])

        self.assertEqual(s.CREATED, response['statusCode'])
        self.assertEqual(result['name'], 'user-1')
        self.assertEqual(result['email'], 'test@gmail.com')

    
    def test_create_user_already_exists(self):

        response = handle(self.create_user_authd_event, None)
        response = handle(self.create_user_authd_event, None)

        self.assertEqual(s.CONFLICT, response['statusCode'])

    
    def test_create_user_no_username(self):

        create_no_body = deepcopy(self.create_user_authd_event)
        create_no_body['body'] = r'{}'

        response = handle(create_no_body, None)

        self.assertEqual(s.BAD_REQUEST, response['statusCode'])


    def test_create_user_no_post_body(self):

        create_no_body = deepcopy(self.create_user_authd_event)
        create_no_body['body'] = None

        response = handle(create_no_body, None)

        self.assertEqual(s.BAD_REQUEST, response['statusCode'])


    def test_get_user(self):

        response = handle(self.create_user_authd_event, None)
        self.assertEqual(s.CREATED, response['statusCode'])

        response = handle(self.get_user_authd_event, None)
        result = json.loads(response['body'])

        self.assertEqual(s.OK, response['statusCode'])
        self.assertEqual(result['name'], 'user-1')
        self.assertEqual(result['email'], 'test@gmail.com')

    
    def test_get_user_no_claims(self):

        result = handle(self.get_user_no_claims_event, None)
        self.assertEqual(result['statusCode'], s.UNAUTHORIZED)


    def test_get_player(self):

        users = []

        for i in range(2):

            username = str(uuid.uuid4())
            users.append(username)

            event = self.replace_event_username(
                self.create_user_authd_event,
                username
            )

            response = handle(event, None)
            self.assertEqual(s.CREATED, response['statusCode'])

        event = self.replace_event_username(
            self.get_player_authd_event,
            users[0]
        )

        event = self.replace_event_path_param(
            event,
            'player_id',
            users[1]
        )

        response = handle(event, None)
        result = json.loads(response['body'])

        self.assertEqual(s.OK, response['statusCode'])
        self.assertTrue('name' in result)
        self.assertTrue('id' in result)
        self.assertEqual(2, len([k for k in result.keys()]))

    
    def test_get_player_not_found(self):

        users = []
        username = str(uuid.uuid4())
        users.append(username)

        event = self.replace_event_username(
            self.create_user_authd_event,
            username
        )

        response = handle(event, None)
        self.assertEqual(s.CREATED, response['statusCode'])

        event = self.replace_event_username(
            self.get_player_authd_event,
            username
        )

        event = self.replace_event_path_param(
            event,
            'player_id',
            'does-not-exist'
        )

        response = handle(event, None)
        result = json.loads(response['body'])

        self.assertEqual(s.NOT_FOUND, response['statusCode'])



