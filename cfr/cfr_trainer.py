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

        # Early stopping parameters
        self.prev_strategies: Dict[str, Dict[Action, float]] = {}

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

    def _calculate_strategy_change(self) -> Dict[int, float]:
        """
        Calculate the total change in strategy probabilities for each player.

        Returns:
            Dictionary mapping player ID to total probability change
        """
        player_changes = {p: 0.0 for p in range(self.num_players)}

        for key, infoset in self.infosets.items():
            current_strategy = infoset.get_average_strategy()

            if key in self.prev_strategies:
                prev_strategy = self.prev_strategies[key]

                # Calculate L1 distance between strategies
                change = 0.0
                for action in current_strategy:
                    curr_prob = current_strategy[action]
                    prev_prob = prev_strategy.get(action, 0.0)
                    change += abs(curr_prob - prev_prob)

                player_changes[infoset.player] += change

            # Update previous strategy
            self.prev_strategies[key] = current_strategy.copy()

        return player_changes

    def train(
        self,
        root_state: GameState,
        iterations: int,
        epsilon: float = 1e-4,
        check_interval: int = 10,
    ) -> int:
        """
        Run CFR for the specified number of iterations with early stopping.

        Args:
            root_state: The initial game state
            iterations: Maximum number of iterations to run
            epsilon: Convergence threshold (sum of all player strategy changes)
            check_interval: How often to check for convergence
        """
        for i in range(iterations):
            self.iteration += 1

            for player in range(self.num_players):
                reach_probs = [1.0] * self.num_players
                self._cfr(root_state.clone(), reach_probs, player)

            self._apply_post_iteration_updates()

            # Check for convergence (skip until we have previous strategies to compare)
            if (
                i > 0
                and (i + 1) % check_interval == 0
                and len(self.prev_strategies) > 0
            ):
                player_changes = self._calculate_strategy_change()
                total_change = sum(player_changes.values())

                if (i + 1) % 100 == 0:
                    print(
                        f"Iteration {i + 1}/{iterations}, Total change: {total_change:.6f}"
                    )
                    for player, change in player_changes.items():
                        print(f"  Player {player}: {change:.6f}")

                if total_change < epsilon:
                    print(f"\nConverged at iteration {i + 1}")
                    print(
                        f"Total strategy change: {total_change:.6f} < epsilon: {epsilon}"
                    )
                    return i
            else:
                # Store strategies even on first check to establish baseline
                if (i + 1) % check_interval == 0:
                    for key, infoset in self.infosets.items():
                        self.prev_strategies[key] = (
                            infoset.get_average_strategy().copy()
                        )

                if (i + 1) % 100 == 0 or i == 0:
                    print(f"Iteration {i + 1}/{iterations}")
        return iterations

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
