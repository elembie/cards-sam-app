from dataclasses import dataclass

@dataclass
class User(object):

    pk: str = None
    sk: str = None
    id: str = None
    name: str = None
    email: str = None
    phone: str = None
    in_game: bool = False
    game_id: str = None

    def __post_init__(self):
        if self.id:
            if not self.pk:
                self.pk = f'USER#{self.id}'
            if not self.sk:
                self.sk = f'ENTITY'

    def to_dict(self):
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in ['pk', 'sk']
        }

    def to_player(self):
        return {
            'id': self.id,
            'name': self.name,
        }
    
    def get_key(self):
        return {
            'pk': self.pk,
            'sk': self.sk,
        }