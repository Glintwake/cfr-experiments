"""
Counterfactual Regret Minimization (CFR) Framework

This module provides a complete framework for implementing CFR and its variants
for imperfect-information games.
"""

from .game_state import GameState
from .cfr_trainer import CFRTrainer
from .action import Action

from typing import Dict, List, Optional


class KuhnPokerState(GameState):
    PASS = Action("Pass")
    BET = Action("Bet")

    def __init__(self, cards: Optional[List[int]] = None, history: str = ""):
        self.cards = cards
        self.history = history

    def is_terminal(self) -> bool:
        return self.history in ["pp", "bp", "pbb", "bb", "pbp"]

    def get_utility(self, player: int) -> float:
        if not self.is_terminal():
            return 0.0

        if self.history == "pp":
            if self.cards[0] > self.cards[1]:
                return 1.0 if player == 0 else -1.0
            elif self.cards[0] < self.cards[1]:
                return -1.0 if player == 0 else 1.0
            else:
                return 0.0

        if self.history == "bp":
            return 1.0 if player == 0 else -1.0

        if self.history == "pbp":
            return -1.0 if player == 0 else 1.0

        if self.history in ("pbb", "bb"):
            if self.cards[0] > self.cards[1]:
                return 2.0 if player == 0 else -2.0
            elif self.cards[0] < self.cards[1]:
                return -2.0 if player == 0 else 2.0
            else:
                return 0.0

        return 0.0

    def get_current_player(self) -> int:
        if self.cards is None:
            return -1
        if self.is_terminal():
            return -1

        if self.history == "":
            return 0

        if self.history in ("p", "b"):
            return 1

        if self.history == "pb":
            return 0

        return -1

    def get_infoset_key(self) -> str:
        player = self.get_current_player()
        if player == -1:
            raise ValueError("No infoset key for chance or terminal nodes")

        card_names = ["J", "Q", "K"]
        card = card_names[self.cards[player]]
        return f"{card}:{self.history}"

    def get_actions(self) -> List[Action]:
        return [self.PASS, self.BET]

    def take_action(self, action: Action) -> "KuhnPokerState":
        if (
            self.cards is None
            and isinstance(action.name, str)
            and len(action.name) == 2
        ):
            new_cards = KuhnPokerState.deal_to_cards(action.name)
            return KuhnPokerState(new_cards, self.history)

        if action == self.PASS:
            new_history = self.history + "p"
        elif action == self.BET:
            new_history = self.history + "b"
        else:
            raise ValueError(f"Unknown action: {action}")

        return KuhnPokerState(self.cards, new_history)

    def get_chance_probabilities(self) -> Dict[Action, float]:
        if self.cards is not None:
            return {}

        deals = [
            Action("JQ"),
            Action("JK"),
            Action("QJ"),
            Action("QK"),
            Action("KJ"),
            Action("KQ"),
        ]
        prob = 1.0 / len(deals)
        return {deal: prob for deal in deals}

    def clone(self) -> "KuhnPokerState":
        cards_copy = self.cards.copy() if self.cards is not None else None
        return KuhnPokerState(cards_copy, self.history)

    @staticmethod
    def deal_to_cards(deal_name: str) -> List[int]:
        card_map = {"J": 0, "Q": 1, "K": 2}
        return [card_map[deal_name[0]], card_map[deal_name[1]]]


def run_kuhn_poker_example(iterations: int = 10000, show_progress: bool = True):
    variants = ["vanilla", "cfr_plus", "lcfr", "dcfr"]
    results = {}

    for variant in variants:
        print(f"\n{'='*60}")
        print(f"Training variant: {variant.upper()}")
        print(f"{'='*60}")

        trainer = CFRTrainer(num_players=2, variant=variant)
        root_state = KuhnPokerState()

        if not show_progress:
            original_print = print
            try:

                def silent_print(*args, **kwargs):
                    pass

                globals()["print"] = silent_print
                trainer.train(root_state, iterations)
            finally:
                globals()["print"] = original_print
        else:
            num_iter = trainer.train(root_state, iterations)

        print()
        trainer.print_strategy()
        results[variant] = (trainer, num_iter)
        print("\n" + "-" * 60)
        print(f"{variant.upper()} training complete\n")

    for variant, [trainer, iters] in results.items():
        print(f"\n{variant.upper()} (num iterations = {iters}):")
        for card in ["J", "Q", "K"]:
            key = f"{card}:"
            infoset = trainer.infosets.get(key)
            if infoset:
                strat = infoset.get_average_strategy()
                p_bet = strat[KuhnPokerState.BET]
                p_pass = strat[KuhnPokerState.PASS]
                print(f"  {card}: Bet {p_bet:.2f}, Pass {p_pass:.2f}")
            else:
                print(f"  {card}: (no data)")

    return results


if __name__ == "__main__":
    results = run_kuhn_poker_example()
