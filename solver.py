"""End-to-end CDCL solver loop.

core.py has the *rules*.
This file is the *engine* that runs them until SAT/UNSAT/timeout.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from core import BoolLiteral, Clause, Core, State
from heuristics import make_heuristic


@dataclass
class SolveStats:
    decisions: int = 0
    conflicts: int = 0
    learned_clauses: int = 0
    propagations: int = 0


@dataclass
class SolveResult:
    status: str  # "SAT", "UNSAT", or "TIMEOUT"
    runtime_sec: float
    stats: SolveStats
    assignment: Dict[str, bool]


def _assignment_dict(state: State) -> Dict[str, bool]:
    out: Dict[str, bool] = {}
    for lit in state.model:
        out[lit.variable] = lit.polarity
    return out


def _is_clause_satisfied(clause: Clause, state: State) -> bool:
    return any(lit in state.model for lit in clause)


def _is_formula_satisfied(state: State) -> bool:
    return all(_is_clause_satisfied(c, state) for c in state.clauses)


def _unit_propagate_all(core: Core, stats: SolveStats) -> None:
    """Naive propagation: scan every clause until nothing changes."""
    changed = True
    while changed and not core.in_conflict:
        changed = False
        for idx in range(len(core.state.clauses)):
            if core.conflict(idx):
                stats.conflicts += 1
                break
            if core.propagate(idx):
                stats.propagations += 1
                changed = True


def _compute_backjump_level(core: Core) -> int:
    assert core.graph.conflict_clause is not None

    decision_lit = core.state.model.get_last_literal()
    uip_neg = decision_lit.negate()
    others = core.graph.conflict_clause - {uip_neg}

    if not others:
        return 0
    return max(core.state.model.get_level(l) for l in others)


def solve_cnf(
    clauses: List[Clause],
    heuristic_name: str = "baseline",
    timeout_sec: float = 10.0,
    seed: int = 0,
    vsids_bump: float = 1.0,
    vsids_decay_factor: float = 0.95,
    vsids_decay_period: int = 50,
    debug: bool = False,
) -> SolveResult:
    state = State(list(clauses))
    core = Core(state)

    heuristic = make_heuristic(
        heuristic_name,
        state.clauses,
        seed=seed,
        bump=vsids_bump,
        decay_factor=vsids_decay_factor,
        decay_period=vsids_decay_period,
    )

    stats = SolveStats()
    start = time.perf_counter()

    def timed_out() -> bool:
        return (time.perf_counter() - start) > timeout_sec

    while True:
        if timed_out():
            return SolveResult("TIMEOUT", time.perf_counter() - start, stats, _assignment_dict(state))

        # 1) Propagate
        _unit_propagate_all(core, stats)

        # 2) Conflict?
        if core.in_conflict:
            if core.fail():
                return SolveResult("UNSAT", time.perf_counter() - start, stats, _assignment_dict(state))

            core.explain()

            learned = core.learn()
            if learned is not None:
                stats.learned_clauses += 1
                heuristic.on_learned_clause(learned)

            heuristic.on_conflict()

            bj = _compute_backjump_level(core)
            core.backjump(bj)

            if debug:
                print("--- conflict handled, backjump to", bj)

            continue

        # 3) SAT?
        if _is_formula_satisfied(state):
            state.sat = True
            return SolveResult("SAT", time.perf_counter() - start, stats, _assignment_dict(state))

        # 4) Decide
        lit = heuristic.pick_decision(state.model)
        if lit is None:
            state.unsat = True
            return SolveResult("UNSAT", time.perf_counter() - start, stats, _assignment_dict(state))

        if core.decide(lit):
            stats.decisions += 1


def solve_dimacs(path: str, **kwargs) -> SolveResult:
    from parser import parse_dimacs
    clauses = parse_dimacs(path)
    return solve_cnf(clauses, **kwargs)