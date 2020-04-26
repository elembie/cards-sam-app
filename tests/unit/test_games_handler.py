import os
import sys
import uuid
import json
from pathlib import Path
from unittest import TestCase
from http import HTTPStatus as s

from . import BaseTestCase

sys.dont_write_bytecode = True

test_path = str(Path(os.getcwd()) / 'services' / 'games' / 'meta')
sys.path.append(test_path)

test_path = str(Path(os.getcwd()) / 'services' / 'users')
sys.path.append(test_path)

from services.games.meta.meta_service.entities import User
from services.games.meta.meta_service.handler import handle
from services.users.user_service.handler import handle as user_handle

class TestGamesHandler(BaseTestCase):

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

    def test_create_game_authd(self):

        event = self.replace_event_username(
            self.create_game_authd_event,
            self.users[0]
        )

        response = handle(event, None)
        result = json.loads(response['body'])

        self.assertEqual(s.CREATED, response['statusCode'])
        self.assertEqual(self.users[0], result['created_by'])
        self.assertTrue(len(result['players']) == 1)
        self.assertEqual(1, result['players_joined'])

    
    def test_create_game_user_in_game(self):

        event = self.replace_event_username(
            self.create_game_authd_event,
            self.users[0]
        )

        response = handle(event, None)
        self.assertEqual(s.CREATED, response['statusCode'])

        event = self.replace_event_username(
            self.create_game_authd_event,
            self.users[0]
        )

        response = handle(event, None)
        self.assertEqual(s.FORBIDDEN, response['statusCode'])

    
    def test_game_add_user(self):

        event = self.replace_event_username(
            self.create_game_authd_event,
            self.users[0]
        )

        response = handle(event, None)
        self.assertEqual(s.CREATED, response['statusCode'])
        
        game_id = json.loads(response['body'])['id']

        event = self.replace_event_username(
            self.join_game_authd_event,
            self.users[1]
        )

        event = self.replace_event_game_id(
            event,
            game_id
        )

        response = handle(event, None)
        result = json.loads(response['body'])

        self.assertEqual(s.OK, response['statusCode'])
        self.assertEqual(2, len(result['players']))
        self.assertEqual(2, result['players_joined'])
        self.assertTrue(self.users[0] in result['players'])
        self.assertTrue(self.users[1] in result['players'])

        user = self.db.get_item(
            Key=
        )


