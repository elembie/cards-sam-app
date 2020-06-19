from dataclasses import dataclass

from boto3.dynamodb.types import TypeSerializer
serializer = TypeSerializer()

@dataclass
class UserGameConnection:

    pk: str = None
    sk: str = None
    connection_id: str = None
    game_id: str = None
    user_id: str = None
    connected_at: int = None

    def __post_init__(self):
        if not self.pk:
            self.pk = f'GAME#{self.game_id}'
        if not self.sk:
            self.sk = f'CONN#{self.connection_id}'

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