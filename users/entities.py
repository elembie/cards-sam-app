from dataclasses import dataclass

@dataclass
class User(object):

    email: str = None
    first_name: str = None
    last_name: str = None
    phone: str = None