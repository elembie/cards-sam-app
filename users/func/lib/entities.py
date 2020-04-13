from dataclasses import dataclass

@dataclass
class User(object):

    id: str = None
    email: str = None
    phone: str = None