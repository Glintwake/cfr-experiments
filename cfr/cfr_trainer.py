from .game_state import GameState
from .info_set import InfoSet
from .action import Action

from typing import Dict, List


class CFRTrainer:
    """
    Main CFR trainer that implements various CFR algorithms.
    """

    def __init__(self, num_players: int = 2, variant: str = "vanilla"):
        """
        Initialize CFR trainer.

        Args:
            num_players: Number of players in the game
            variant: CFR variant to use:
                - "vanilla": Standard CFR
                - "cfr_plus": CFR+ (regret floor, linear averaging)
                - "lcfr": Linear CFR
                - "dcfr": Discounted CFR (default params: 3/2, 0, 2)
        """
        self.num_players = num_players
        self.variant = variant
        self.infosets: Dict[str, InfoSet] = {}
        self.iteration = 0

        # DCFR parameters (alpha, beta, gamma)
        self.alpha = 1.5
        self.beta = 0.0
        self.gamma = 2.0

    def set_dcfr_params(self, alpha: float, beta: float, gamma: float):
        """Set DCFR parameters."""
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def get_infoset(self, state: GameState) -> InfoSet:
        """Get or create an InfoSet for the given state."""
        key = state.get_infoset_key()

        if key not in self.infosets:
            player = state.get_current_player()
            actions = state.get_actions()
            self.infosets[key] = InfoSet(key, actions, player)

        return self.infosets[key]

    def train(self, root_state: GameState, iterations: int):
        """
        Run CFR for the specified number of iterations.

        Args:
            root_state: The initial game state
            iterations: Number of iterations to run
        """
        for i in range(iterations):
            self.iteration += 1

            for player in range(self.num_players):
                reach_probs = [1.0] * self.num_players
                self._cfr(root_state.clone(), reach_probs, player)

            self._apply_post_iteration_updates()

            if (i + 1) % 100 == 0 or i == 0:
                print(f"Iteration {i + 1}/{iterations}")

    def _cfr(
        self, state: GameState, reach_probs: List[float], updating_player: int
    ) -> float:
        """
        Recursive CFR calculation.

        Args:
            state: Current game state
            reach_probs: Reach probabilities for each player
            updating_player: Which player is updating regrets this iteration

        Returns:
            Expected utility for the updating player
        """
        if state.is_terminal():
            return state.get_utility(updating_player)

        current_player = state.get_current_player()

        if current_player == -1:
            action_probs = state.get_chance_probabilities()
            expected_value = 0.0
            for action, prob in action_probs.items():
                new_state = state.take_action(action)
                expected_value += prob * self._cfr(
                    new_state, reach_probs, updating_player
                )
            return expected_value

        infoset = self.get_infoset(state)
        strategy = infoset.get_strategy(reach_probs[current_player])

        action_values = {}
        expected_value = 0.0

        for action in infoset.actions:
            new_reach_probs = reach_probs.copy()
            new_reach_probs[current_player] *= strategy[action]

            new_state = state.take_action(action)
            action_values[action] = self._cfr(
                new_state, new_reach_probs, updating_player
            )
            expected_value += strategy[action] * action_values[action]

        if current_player == updating_player:
            cfr_reach = 1.0
            for p in range(self.num_players):
                if p != current_player:
                    cfr_reach *= reach_probs[p]

            for action in infoset.actions:
                regret = action_values[action] - expected_value
                infoset.update_regret(action, cfr_reach * regret)

        return expected_value

    def _apply_post_iteration_updates(self):
        """Apply variant-specific updates after each iteration."""
        t = self.iteration

        if self.variant == "cfr_plus":
            for infoset in self.infosets.values():
                infoset.apply_regret_floor()

        elif self.variant == "lcfr":
            discount = t / (t + 1)
            for infoset in self.infosets.values():
                infoset.discount_regrets(discount, discount)
                infoset.discount_strategy(discount)

        elif self.variant == "dcfr":
            pos_discount = (t**self.alpha) / (t**self.alpha + 1)
            neg_discount = (t**self.beta) / (t**self.beta + 1)
            strat_discount = (t / (t + 1)) ** self.gamma

            for infoset in self.infosets.values():
                infoset.discount_regrets(pos_discount, neg_discount)
                infoset.discount_strategy(strat_discount)

    def get_strategy_profile(self) -> Dict[str, Dict[Action, float]]:
        """
        Get the average strategy for all infosets.
        This is the Nash equilibrium approximation.
        """
        return {
            key: infoset.get_average_strategy()
            for key, infoset in self.infosets.items()
        }

    def print_strategy(self, infoset_key: str | None = None):
        """Print the average strategy for a specific infoset."""
        if infoset_key is None:
            print("=== Full Strategy ===")
            for key, infoset in self.infosets.items():
                print(f"{key}: {infoset.get_average_strategy()}")
            return

        if infoset_key not in self.infosets:
            print(f"InfoSet {infoset_key} not found")
            return

        infoset = self.infosets[infoset_key]
        strategy = infoset.get_average_strategy()

        print(f"\nInfoSet: {infoset_key} (Player {infoset.player})")
        for action, prob in strategy.items():
            print(f"  {action}: {prob:.4f}")
