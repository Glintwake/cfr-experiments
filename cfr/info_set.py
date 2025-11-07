from collections import defaultdict
from typing import Dict, List
from .action import Action


class InfoSet:
    """
    Represents an information set (infoset) - a collection of game states
    that are indistinguishable to a player.
    """

    def __init__(self, key: str, actions: List[Action], player: int):
        self.key = key
        self.actions = actions
        self.player = player
        self.num_actions = len(actions)

        self.regret_sum = defaultdict(float)
        self.strategy_sum = defaultdict(float)
        self.reach_probability_sum = 0.0

        for action in actions:
            self.regret_sum[action] = 0.0
            self.strategy_sum[action] = 0.0

    def get_strategy(self, realization_weight: float = 1.0) -> Dict[Action, float]:
        """
        Get current strategy using Regret Matching.
        Returns a probability distribution over actions.
        """
        strategy = {}
        normalizing_sum = 0.0

        for action in self.actions:
            regret = self.regret_sum[action]
            strategy[action] = max(0.0, regret)
            normalizing_sum += strategy[action]

        if normalizing_sum > 0:
            for action in self.actions:
                strategy[action] /= normalizing_sum
        else:
            uniform_prob = 1.0 / self.num_actions
            for action in self.actions:
                strategy[action] = uniform_prob

        for action in self.actions:
            self.strategy_sum[action] += realization_weight * strategy[action]

        self.reach_probability_sum += realization_weight

        return strategy

    def get_average_strategy(self) -> Dict[Action, float]:
        """
        Get the average strategy across all iterations.
        This is what converges to Nash equilibrium.
        """
        avg_strategy = {}
        normalizing_sum = 0.0

        for action in self.actions:
            normalizing_sum += self.strategy_sum[action]

        if normalizing_sum > 0:
            for action in self.actions:
                avg_strategy[action] = self.strategy_sum[action] / normalizing_sum
        else:
            uniform_prob = 1.0 / self.num_actions
            for action in self.actions:
                avg_strategy[action] = uniform_prob

        return avg_strategy

    def update_regret(self, action: Action, regret: float):
        """Add regret for a specific action."""
        self.regret_sum[action] += regret

    def apply_regret_floor(self):
        """Apply regret floor at zero (CFR+ style)."""
        for action in self.actions:
            if self.regret_sum[action] < 0:
                self.regret_sum[action] = 0.0

    def discount_regrets(self, pos_discount: float, neg_discount: float):
        """
        Discount regrets (for DCFR variants).
        pos_discount: multiplier for positive regrets
        neg_discount: multiplier for negative regrets
        """
        for action in self.actions:
            if self.regret_sum[action] > 0:
                self.regret_sum[action] *= pos_discount
            else:
                self.regret_sum[action] *= neg_discount

    def discount_strategy(self, discount: float):
        """Discount contributions to average strategy."""
        for action in self.actions:
            self.strategy_sum[action] *= discount
        self.reach_probability_sum *= discount

    def __str__(self):
        return f"InfoSet({self.key}, player={self.player}, actions={[str(a) for a in self.actions]})"
