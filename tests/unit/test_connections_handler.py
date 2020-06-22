import os
import sys
import uuid
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from http import HTTPStatus as s

from . import BaseTestCase

sys.dont_write_bytecode = True

test_path = str(Path(os.getcwd()) / 'services' / 'games' / 'meta')
sys.path.append(test_path)

test_path = str(Path(os.getcwd()) / 'services' / 'users')
sys.path.append(test_path)

test_path = str(Path(os.getcwd()) / 'services' / 'connections')
sys.path.append(test_path)

from services.games.meta.meta_service.entities import User
from services.games.meta.meta_service.handler import handle as games_handle
from services.users.user_service.handler import handle as user_handle

from services.connections.connection_service.handler import handle

class TestConnectionsHandler(BaseTestCase):

    def setUp(self):

        super().setUp()

        with open('tests/events/create-user-authd.json', 'r') as f:
                create_user_authd_event = json.load(f)

        # add 4 random users to db
        self.users = []
        for _ in range(4):

            guid = str(uuid.uuid4())
            self.users.append(guid)

            event = self.replace_event_username(
                create_user_authd_event,
                guid
            )
            
            response = user_handle(event, None)
            self.assertEqual(s.CREATED, response['statusCode'])

        with open('tests/events/create-game-authd.json') as f:
            self.create_game_authd_event = json.load(f)

        with open('tests/events/join-game-authd.json') as f:
            self.join_game_authd_event = json.load(f)

        with open('tests/events/websocket-connect.json') as f:
            self.websocket_connect_event = json.load(f)

        with open('tests/events/game-update-stream.json') as f:
            self.game_update_stream_event = json.load(f)

        event = self.replace_event_username(
            self.create_game_authd_event,
            self.users[0]
        )

        response = games_handle(event, None)
        self.game_id = json.loads(response['body'])['id']
        self.game_update_stream_event['Records'][1]['dynamodb']['Keys']['pk']['s'] = f'GAME#{self.game_id}'

        self.assertEqual(s.CREATED, response['statusCode'])

    
    def test_connect_with_no_token(self):

        connect_no_token = self.replace_query_params(
            self.websocket_connect_event,
            'token',
            None
        )

        response = handle(connect_no_token, None)
        self.assertEqual(s.UNAUTHORIZED, response['statusCode'])


    def test_connect_with_no_connection_id(self):

        connect_no_id = self.replace_request_context_param(
            self.websocket_connect_event,
            'connectionId',
            None
        )

        response = handle(connect_no_id, None)
        self.assertEqual(s.BAD_REQUEST, response['statusCode'])

    
    def test_connect_invalid_jwt(self):

        response = handle(self.websocket_connect_event, None)
        self.assertEqual(s.UNAUTHORIZED, response['statusCode'])


    def test_stream_handler_game_update(self):

        with patch('connection_service.token.validate_and_decode') as mock_validator:
            mock_validator.side_effect = lambda x: {'sub': self.users[0]}

            response = handle(self.websocket_connect_event, None)
            response = handle(self.game_update_stream_event, None)






        