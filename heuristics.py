"""Decision heuristics for CDCL.

- Baseline: pick a random unassigned literal.
- VSIDS: bump literals in learned clauses, decay sometimes, pick max activity.
"""

from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional, Set

from core import BoolLiteral, Clause, Model


def extract_variables(clauses: Iterable[Clause]) -> List[str]:
    """Collect all variable names that appear in the CNF."""
    vars_set: Set[str] = set()
    for clause in clauses:
        for lit in clause:
            vars_set.add(lit.variable)
    return sorted(vars_set)


class RandomBaselineHeuristic:
    """Baseline: pick an unassigned literal uniformly at random."""

    def __init__(self, variables: List[str], seed: int = 0):
        self.variables = variables
        self.rng = random.Random(seed)

    def pick_decision(self, model: Model) -> Optional[BoolLiteral]:
        unassigned_vars = [
            v
            for v in self.variables
            if BoolLiteral.make_pos(v) not in model and BoolLiteral.make_neg(v) not in model
        ]
        if not unassigned_vars:
            return None

        v = self.rng.choice(unassigned_vars)
        polarity = self.rng.choice([True, False])  # True means v, False means ¬v
        return BoolLiteral(v, polarity)

    def on_learned_clause(self, clause: Clause) -> None:
        return

    def on_conflict(self) -> None:
        return


class VSIDSHeuristic:
    """Very small VSIDS implementation (easy version)."""

    def __init__(
        self,
        variables: List[str],
        seed: int = 0,
        bump: float = 1.0,
        decay_factor: float = 0.95,
        decay_period: int = 50,
    ):
        self.variables = variables
        self.rng = random.Random(seed)

        self.bump = bump
        self.decay_factor = decay_factor
        self.decay_period = decay_period
        self.conflict_count = 0

        # Activity for both polarities.
        self.activity: Dict[BoolLiteral, float] = {}
        for v in self.variables:
            self.activity[BoolLiteral.make_pos(v)] = 0.0
            self.activity[BoolLiteral.make_neg(v)] = 0.0

    def pick_decision(self, model: Model) -> Optional[BoolLiteral]:
        candidates: List[BoolLiteral] = []
        best_score = float("-inf")

        for v in self.variables:
            if BoolLiteral.make_pos(v) in model or BoolLiteral.make_neg(v) in model:
                continue

            for lit in (BoolLiteral.make_pos(v), BoolLiteral.make_neg(v)):
                score = self.activity.get(lit, 0.0)
                if score > best_score:
                    best_score = score
                    candidates = [lit]
                elif score == best_score:
                    candidates.append(lit)

        if not candidates:
            return None
        return self.rng.choice(candidates)

    def on_learned_clause(self, clause: Clause) -> None:
        for lit in clause:
            self.activity[lit] = self.activity.get(lit, 0.0) + self.bump

    def on_conflict(self) -> None:
        self.conflict_count += 1
        if self.decay_period > 0 and (self.conflict_count % self.decay_period == 0):
            for lit in list(self.activity.keys()):
                self.activity[lit] *= self.decay_factor


def make_heuristic(
    name: str,
    clauses: Iterable[Clause],
    seed: int = 0,
    bump: float = 1.0,
    decay_factor: float = 0.95,
    decay_period: int = 50,
):
    variables = extract_variables(clauses)

    name = name.lower().strip()
    if name in {"baseline", "random"}:
        return RandomBaselineHeuristic(variables, seed=seed)
    if name in {"vsids"}:
        return VSIDSHeuristic(
            variables,
            seed=seed,
            bump=bump,
            decay_factor=decay_factor,
            decay_period=decay_period,
        )
    raise ValueError(f"Unknown heuristic: {name}")