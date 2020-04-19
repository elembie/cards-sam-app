import sys
import json

from unittest import TestCase
from unittest.mock import patch, MagicMock

sys.dont_write_bytecode = True

from functions.users.resource.entities import User
from functions.users.resource.handler import handle, get_user_from_claims

class TestUserHanlder(TestCase):

    def setUp(self):
        with open('tests/events/get-user-authd.json', 'r') as f:
            self.get_user_authd_event = json.load(f)   

        with open('tests/events/get-user-no-claims.json', 'r') as f:
            self.get_user_no_claims_event = json.load(f)    


    def test_get_user_from_event_clams(self):

        user = get_user_from_claims(self.get_user_authd_event)
        self.assertEqual(type(user), User)
        self.assertEqual(user.id, '04f19018-c27e-4097-b84c-49ed474d0134')
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(user.phone, '+61999999999')


    def test_get_user_authorized(self):

        result = handle(self.get_user_authd_event, None)
        self.assertEqual(result['statusCode'], 200)

    
    def test_get_user_no_claims(self):

        result = handle(self.get_user_no_claims_event, None)
        self.assertEqual(result['statusCode'], 400)
        
