import json
from unittest import TestCase


class TestGamesHandler(TestCase):

    def setUp(self):
        with open('tests/events/create-game-authd.json') as f:
            self.create_game_authd_event = json.load(f)

    # def test_create_game_authd(self):

    #     result = handle(self.create_game_authd_event, None)
