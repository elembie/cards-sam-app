from enum import Enum
from hashlib import md5
from random import shuffle
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict

from game.constants import SUITS, RANKS
from game.exceptions import InvalidAction, InvalidState
from game.entities import (
    Card, Meta, State, Status, Player
)

class Game(object):

    def __init__(self, game: dict):
        
        if not game:
            raise ValueError('Game cannot be None')

        self.game_id: str = game['game_id']
        self.meta: Meta = Meta(**game['meta'])
        self.state: State = State(**game['state'])

    
    @classmethod
    def new(cls, player_id: str = None, n_players: int = 3) -> 'Game':

        game = {
            'game_id': None,
            'meta': asdict(Meta(total_players=n_players)),
            'state': asdict(State()),
        }

        deck = [Card(suit=s, rank=r) for s in SUITS for r in RANKS]
        shuffle(deck)

        game['state']['stack'] = [ asdict(c) for c in deck ]

        game = cls(game)

        if player_id:
            game.add_player(player_id)

        game.meta.host = player_id

        return game

    
    def to_dict(self) -> dict:
        return {
            'game_id': self.game_id,
            'meta': asdict(self.meta),
            'state': asdict(self.state)
        }

    
    def get_player_index(self, player_id: str) -> int:
        
        try:
            return [ p.id for p in self.state.players ].index(player_id)
        except ValueError:
            raise ValueError(f'Cannot find player with id {player_id}')

    
    def add_player(self, player_id: str):

        n_players = self.state.n_players

        self.state.players.append(
            Player(
                id=player_id,
                order=n_players,
                is_dealer=n_players == 0,
                is_active=n_players == 1,
            )
        )
        
        if self.state.n_players == self.meta.total_players:
            self.state.status = Status.DEAL

    
    def deal(self, player_id):

        if self.state.status != Status.DEAL:
            raise InvalidState('Not ready to deal')

        player = self.state.get_player(player_id)

        if not player.is_dealer:
            raise InvalidAction('Player is not the dealer')

        for player in self.state.players:
            for _ in range(3):
                player.hidden.append(self.state.stack.pop())
                player.table.append(self.state.stack.pop())
                player.hand.append(self.state.stack.pop())

        self.state.status = Status.PREP

    
    def swap_table(self, player_id: str, hand_id: str, table_id: str):

        if self.state.status != Status.PREP:
            raise InvalidState('Cannot swap cards when not in prep stage')
        
        idx = self.get_player_index(player_id)

        self.state.players[idx].swap_table(
            hand_id=hand_id,
            table_id=table_id
        )


    def player_ready(self, player_id):
        
        if self.state.status != Status.PREP:
            raise InvalidState('Cannot be ready outside of prep stage')

        idx = self.get_player_index(player_id)

        self.state.players[idx].is_ready = True

        if self.state.players_ready == self.meta.total_players:
            self.state.status = Status.PLAYING


    def play_cards(self, player_id: str, card_ids: List[str]):
        
        if self.state.status != Status.PLAYING:
            raise InvalidState('Cannot play card outside of playing stage')

        player = self.state.get_player(player_id)

        if not player.is_active:
            raise InvalidState('Player is not active so cannot play')

        elif not player.has_hand and not player.has_table:
            # if we're playing hidden cards they will temporarily be in the hand
            raise InvalidState('Player has no cards to play')

        elif player.can_burn:
            raise InvalidAction('Player is able to burn the table')

        card_set = player.hand if player.has_hand else player.table

        cards = [ c for c in card_set if c.id in card_ids ]

        # cards must be of same rank to play together
        if not all([c.value == cards[0].value for c in cards]):
            raise InvalidAction('Cards are not all of the same value')

        # must be equal for all cards as per previous check
        value = cards[0].value
        is_special = cards[0].is_special

        # playing 4 cards means we can burn
        player.can_burn = len(cards) >= 4 or value == 10

        # check for invalid play of 'normal' cards
        if not is_special:
            if self.state.current_value == 7:
                if value > 7:
                    raise InvalidAction('Must play equal or below a 7')
            elif value < self.state.current_value:
                raise InvalidAction('Must play a rank equal or higher')

        # cards are fine to play
        for card in cards:
            idx = [ c.id for c in card_set ].index(card.id)
            played_card = card_set.pop(idx)
            played_card.played_by = player.id
            self.state.table.append(played_card)

        # if previous 4 cards are same value then we can burn
        if len(self.state.table) >= 4:
            player.can_burn = player.can_burn or all(c.value == value for c in self.state.table[-4:])

        # normal cards set a new value
        if not is_special and not player.can_burn:
            self.state.current_value = value

        # can play any card after a 2 or when burnt
        elif value == 2 or player.can_burn:
            self.state.current_value = 0

        # 3 is invisible
        elif value == 3:
            pass

        # change active player if not burning
        if not player.can_burn:
            self._end_turn()


    def play_hidden(self, player_id):

        if self.state.status != Status.PLAYING:
            raise InvalidState('Cannot play card outside of playing stage')

        player = self.state.get_player(player_id)

        if player.has_hand or player.has_table:
            raise InvalidAction('Player cannot play hidden cards yet')

        card = player.hidden.pop()
        card.played_by = player.id

        if card.is_special:
            player.hand.append(card)
            self.play_cards(player.id, [card.id])

        elif self.state.current_value == 7:
            if card.value <= 7:
                player.hand.append(card)
                self.play_cards(player_id, [card.id])

        elif card.value >= self.state.current_value:
            player.hand.append(card)
            self.play_cards(player_id, [card.id])

        else:
            self.state.table.append(card)
            # player must need to pick up
            player.can_play = False


    def burn_table(self, player_id: str):

        if self.state.status != Status.PLAYING:
            raise InvalidState('Cannot burn when not in playing stage')

        player = self.state.get_player(player_id)

        if not player:
            raise IndexError(f'Could not find player with ID {player_id} in game')

        if not player.is_active and not player.can_burn:
            raise InvalidAction('Player is not active, or is not able to burn the deck')

        self.state.burn_table()
        player.can_burn = False

    
    def pickup_table(self, player_id: str):

        if self.state.status != Status.PLAYING:
            raise InvalidState('Cannot pickup when not in playing stage')

        player = self.state.get_player(player_id)

        if not player:
            raise IndexError(f'Could not find player with ID {player_id} in game')

        if not player.is_active:
            raise InvalidAction('Cannot pick up if the player is not active')

        while len(self.state.table) > 0:
            player.hand.append(self.state.table.pop())

        self.state.current_value = 0

        self._end_turn()

        
    def _end_turn(self):

        player = self.state.active_player

        # pick up if needed and cards are available
        while len(player.hand) < 3 and len(self.state.stack) > 0:
            player.hand.append(self.state.stack.pop())

        if not player.has_hand and not player.has_table and not player.has_hidden:
            player.is_out = True

        if self.state.players_remaining == 1:

            # only player left so end round
            self._end_roud()
        
        else:

            next_player = self.state.next_player

            player.is_active = False
            next_player.is_active = True

            next_player.can_play = self.state.player_can_play(next_player.id)
        

    def _end_roud(self):
        
        self.state.status = Status.END

        losing_player: Player = next((p for p in self.state.players if not p.is_out), None)

        if not losing_player:
            raise InvalidState('Game error - round ended but no players remaining')

        losing_player.is_sh = True
        losing_player.sh_count += 1



    