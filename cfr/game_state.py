from typing import Dict, List
from .action import Action
from abc import ABC, abstractmethod


class GameState(ABC):
    """
    Abstract base class for a game state.
    Subclass this to implement specific games.
    """

    @abstractmethod
    def is_terminal(self) -> bool:
        """Returns True if this is a terminal state."""
        pass

    @abstractmethod
    def get_utility(self, player: int) -> float:
        """Returns the utility for the given player at this terminal state."""
        pass

    @abstractmethod
    def get_current_player(self) -> int:
        """Returns which player acts at this state (or -1 for chance)."""
        pass

    @abstractmethod
    def get_infoset_key(self) -> str:
        """
        Returns a unique key identifying the information set.
        States with the same key are indistinguishable to the acting player.
        """
        pass

    @abstractmethod
    def get_actions(self) -> List[Action]:
        """Returns list of available actions at this state."""
        pass

    @abstractmethod
    def take_action(self, action: Action) -> "GameState":
        """Returns the new state after taking the given action."""
        pass

    @abstractmethod
    def get_chance_probabilities(self) -> Dict[Action, float]:
        """
        If current player is chance (-1), return probability distribution over actions.
        Otherwise, return empty dict.
        """
        pass

    @abstractmethod
    def clone(self) -> "GameState":
        """Return a deep copy of this state."""
        pass
