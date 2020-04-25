from typing import List, Any
from uuid import uuid4
from dataclasses import dataclass, field

from boto3.dynamodb.types import TypeSerializer

serializer = TypeSerializer()

class GameTypesEnum:

    SHD = 'SHD'
    CTB = 'CTB'

    @classmethod
    def to_list(cls):
        return [ 
            v for k, v in cls.__dict__.items() 
            if type(v) == str and '__' not in k 
        ]

@dataclass
class User:
    id: str = None
    in_game: bool = False


@dataclass
class GameMeta:

    pk: str = None
    sk: str = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_by: str = None
    private: bool = False
    game_type: str = GameTypesEnum.SHD

    table_size: int = 4
    players_joined: int = 0
    players: List[str] = field(default_factory=list)
    invited_players: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.pk = f'GAME#{self.id}' if not self.pk else self.pk
        self.sk = f'META' if not self.sk else self.sk

    def get_key(self) -> dict:
        return GameMeta.make_key(self.id)

    def to_dict(self):
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in ['pk', 'sk']
        }

    @classmethod
    def make_key(cls, game_id):
        return {
            'pk': f'GAME#{game_id}',
            'sk': f'META'
        }



@dataclass
class GameUser:

    pk: str = None
    sk: str = None
    game_id: str = None
    user_id: str = None
    connection_id: str = None
    connected: bool = False

    def __post_init__(self):
        if not self.pk:
            self.pk = f'GAME#{self.game_id}'
        if not self.sk:
            self.sk = f'USER#{self.user_id}'

    def to_dict(self):
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in ['pk', 'sk']
        }

    def to_dynamo(self):
        return {
            k: serializer.serialize(v)
            for k, v in self.__dict__.items()
        }



@dataclass
class Game:

    meta: GameMeta = None
    players: List[GameUser] = field(default_factory=list)
    state: Any = None

