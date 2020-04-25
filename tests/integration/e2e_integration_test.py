from dataclasses import dataclass, asdict

import boto3

from api import (
    log,
    create_user,
    authenticate_and_get_token,
    delete_user
)

@dataclass
class User:
    username: str = None
    password: str = None

user_1 = User(username='test_1@test.com', password='cardstest2020')

create_user(**asdict(user_1))
token = authenticate_and_get_token(**asdict(user_1))
delete_user(user_1.username)