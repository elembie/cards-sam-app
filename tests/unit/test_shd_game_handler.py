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

test_path = str(Path(os.getcwd()) / 'services' / 'games' / 'shd')
sys.path.append(test_path)

test_path = str(Path(os.getcwd()) / 'services' / 'connections')
sys.path.append(test_path)

test_path = str(Path(os.getcwd()) / 'services' / 'users')
sys.path.append(test_path)

from services.games.meta.meta_service.entities import User
from services.games.meta.meta_service.handler import handle as meta_handle
from services.users.user_service.handler import handle as user_handle
from services.connections.connection_service import handler as conn_handler

from services.games.shd.shd_service.handler import handle

class TestShdGameHandler(BaseTestCase):

    def setUp(self):

        super().setUp()

        with open('tests/events/create-user-authd.json', 'r') as f:
            create_user_authd_event = json.load(f)

        # add 4 random users to db
        self.users = []
        for _ in range(3):

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

        with open('tests/events/exit-game-authd.json') as f:
            self.exit_game_authd_event = json.load(f)

        with open('tests/events/get-game-authd.json') as f:
            self.get_game_authd_event = json.load(f)

        with open('tests/events/websocket-connect.json') as f:
            self.websocket_connect_event = json.load(f)

        with open('tests/events/sh-websocket-message.json') as f:
            self.websocket_message_event = json.load(f)

        # create game and add first user
        event = self.replace_event_username(
            self.create_game_authd_event,
            self.users[0]
        )

        response = meta_handle(event, None)
        self.assertEqual(s.CREATED, response['statusCode'])
        
        self.game_id = json.loads(response['body'])['id']

        # add another two players (game full)
        for i in range(1, len(self.users)):

            event = self.replace_event_username(
                self.join_game_authd_event,
                self.users[i]
            )

            event = self.replace_event_game_id(
                event,
                self.game_id
            )

            response = meta_handle(event, None)
            self.assertEqual(s.OK, response['statusCode'])

        for i in range(len(self.users)):

            with patch.object(conn_handler, 'validate_and_decode', return_value={'sub': self.users[i]}):

                event = self.replace_request_context_param(
                    self.websocket_connect_event,
                    'connectionId',
                    self.users[i]
                )

                response = conn_handler.handle(event, None)

    
    def test_start_game_deal(self):

        event = self.replace_wbs_event_context(
            self.websocket_message_event,
            'connectionId',
            self.users[0]
        )

        event = self.replace_wbs_event_body(
            event,
            {
                'gameId': self.game_id,
                'type': 'DEAL'
            }
        )

        handle(event, None)

    def test_swap_cards(self):

        event = self.replace_wbs_event_context(
            self.websocket_message_event,
            'connectionId',
            self.users[0]
        )

        event = self.replace_wbs_event_body(
            event,
            {
                'gameId': self.game_id,
                'type': 'DEAL'
            }
        )

        handle(event, None)

        event = self.replace_event_username(
            self.get_game_authd_event,
            self.users[0]
        )

        response = json.loads(meta_handle(event, None)['body'])
        player = response['player']
        hand_id = player['hand'][0]['id']
        table_id = player['table'][0]['id']

        event = self.replace_wbs_event_context(
            self.websocket_message_event,
            'connectionId',
            self.users[0]
        )

        event = self.replace_wbs_event_body(
            event,
            {
                'gameId': self.game_id,
                'type': 'SWAP',
                'data': {
                    'hand': hand_id,
                    'table': table_id
                }
            }
        )

        handle(event, None)

        print(response)


