from dataclasses import dataclass

@dataclass
class User(object):

    pk: str = None
    sk: str = None
    id: str = None
    email: str = None
    phone: str = None
    in_game: bool = False

    def __post_init__(self):
        
        if self.id:
            if not self.pk:
                self.pk = f'USER#{self.id}'
            if not self.sk:
                self.sk = f'#META#{self.id}'