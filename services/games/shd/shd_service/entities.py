from enum import Enum
from hashlib import md5
from random import shuffle
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict

from shd_service.exceptions import InvalidState
from shd_service.constants import RANKS, SPECIALS, SUITS

@dataclass
class Card(object):

    id: str = None
    suit: str = None
    rank: str = None
    value: int = None
    suit_value: int = None
    is_special: bool = None
    played_by: str = None

    def __post_init__(self):
        self.value = RANKS.index(self.rank) + 2
        self.suit_value = SUITS.index(self.suit)
        self.is_special = self.rank in SPECIALS
        self.id = md5((self.suit + str(self.value)).encode('utf-8')).hexdigest()


@dataclass
class Player(object):

    id: str = None
    order: int = None
    sh_count: int = 0
    hand: List[Card] = field(default_factory=list)
    table: List[Card] = field(default_factory=list)
    hidden: List[Card] = field(default_factory=list)
    is_dealer: bool = False
    is_active: bool = False
    is_ready: bool = False
    is_out: bool = False
    is_sh: bool = False
    can_burn: bool = False
    can_play: bool = False

    def __post_init__(self):
        '''populate objects if dicts given'''
        self.hand = [ Card(**c) for c in self.hand if type(c) == dict]
        self.table = [ Card(**c) for c in self.table if type(c) == dict]
        self.hidden = [ Card(**c) for c in self.hidden if type(c) == dict]

    @property
    def has_hand(self) -> bool:
        return len(self.hand) > 0

    @property
    def has_table(self) -> bool:
        return len(self.table) > 0

    @property
    def has_hidden(self) -> bool:
        return len(self.hidden) > 0

    @property
    def has_special(self):
        
        if self.has_hand:
            return any((c.is_special for c in self.hand))
        else:
            return any((c.is_special for c in self.table))


    def swap_table(self, hand_id: str = None, table_id: str = None):

        try:
            hand_index = [ c.id for c in self.hand ].index(hand_id)
        except ValueError:
            raise ValueError('Cannot find requested card in players hand')

        try:
            table_index = [ c.id for c in self.table ].index(table_id)
        except ValueError:
            raise ValueError('Cannot find card on players table')

        self.hand.append(self.table.pop(table_index))
        self.table.append(self.hand.pop(hand_index))


    def get_hand_index(self, card_id: str) -> int:

        try:
            return [ c.id for c in self.hand ].index(card_id)
        except ValueError:
            raise ValueError(f'Cannot find card with id {card_id} in players hand')


    def get_table_index(self, card_id: str) -> int:

        try:
            return [ c.id for c in self.table ].index(card_id)
        except ValueError:
            raise ValueError(f'Cannot find card with id {card_id} on players table')


@dataclass
class Meta(object):
    total_players: int = 3


class Status(object):
    INIT: str = 'INIT'
    DEAL: str = 'DEAL'
    PREP: str = 'PREP'
    PLAYING: str = 'PLAYING'
    END: str = 'END'


@dataclass
class State(object):

    status: str = Status.INIT
    current_value: int = 0
    total_players: int = 3
    players: List[Player] = field(default_factory=list)
    table: List[Card] = field(default_factory=list)
    stack: List[Card] = field(default_factory=list)
    dead: List[Card] = field(default_factory=list)

    def __post_init__(self):
        '''populate objects if dicts given'''
        self.players = [ Player(**p) for p in self.players if type(p) == dict ]
        self.table = [ Card(**c) for c in self.table if type(c) == dict ]
        self.stack = [ Card(**c) for c in self.stack if type(c) == dict ]
        self.dead = [ Card(**c) for c in self.dead if type(c) == dict ]

    @property
    def n_players(self) -> int:
        return len(self.players)

    @property
    def players_ready(self) -> int:
        return len([ p for p in self.players if p.is_ready ])

    @property
    def players_remaining(self) -> int:
        return len([ p for p in self.players if not p.is_out ])

    @property
    def active_player(self) -> Player:

        player = next((p for p in self.players if p.is_active), None)
        if not player:
            raise IndexError('Cannot find active player')
        return player

    @property
    def next_player(self) -> Player:

        next_order = self.active_player.order + 1
        if next_order >= self.n_players:
            next_order = 0
        return next(
            (p for p in self.players if p.order >= next_order and not p.is_out), 
            None
        )
        

    def get_player(self, player_id: str) -> Player:

        player = next((p for p in self.players if p.id == player_id), None)
        if not player:
            raise IndexError(f'Cannot find player with ID {player_id}')
        return player


    def player_can_play(self, player_id) -> bool:

        player = self.get_player(player_id)
        
        if player.has_special:
            return True

        if self.current_value == 7:

            if player.has_hand:
                return any((c.value <= self.current_value for c in player.hand))
                
            elif player.has_table:
                return (any(c.value <= self.current_value for c in player.table))

        else:

            if player.has_hand:
                return any((c.value >= self.current_value for c in player.hand))
                
            elif player.has_table:
                return (any(c.value >= self.current_value for c in player.table))

        if not player.has_hand and not player.has_table and player.has_hidden:
            return True


    def burn_table(self):
        self.dead += self.table
        self.table = []
        self.current_value = 0
