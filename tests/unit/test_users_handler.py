import sys
import json
from unittest import TestCase

sys.dont_write_bytecode = True

from users.func.lib.entities import User
from users.func.handler import handle, get_user_from_claims

class TestUserHanlder(TestCase):

    def setUp(self):
        with open('events/get-user-authd.json', 'r') as f:
            self.get_user_authd_event = json.load(f)        

    def test_get_user_from_event_clams(self):

        user = get_user_from_claims(self.get_user_authd_event)
        self.assertEqual(type(user), User)
        self.assertEqual(user.id, '04f19018-c27e-4097-b84c-49ed474d0134')
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(user.phone, '+61999999999')

    def test_get_user_authorized(self):

        result = handle(self.get_user_authd_event, None)

        print(json.dumps(result, indent=3))
        self.assertEqual(result['statusCode'], 200)
        
