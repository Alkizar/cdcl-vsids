# Makes type hints behave as forward references, allowing us to use the class name in type hints before the class is defined.
from __future__ import annotations
# Lets us clone graphs without worrying about shared references.
from copy import deepcopy
# Type hints for better readability and error checking.
from typing import Dict, List, Optional, Set

class BoolLiteral:
    """
    A boolean literal for `variable`. 
    polarity:
    * True  means the literal is positive (x)
    * False means the literal is negative (¬x)
    """
    def __init__(self, variable: str, polarity: bool):
        self.variable = variable
        self.polarity = polarity

    def __repr__(self) -> str:
        prefix = ""
        if not self.polarity:
            prefix = "¬"
        return prefix + self.variable

    def __eq__(self, other) -> bool:
        if not isinstance(other, BoolLiteral):
            return False
        return self.variable == other.variable and self.polarity == other.polarity

    def __hash__(self):
        return hash((self.variable, self.polarity))

    def is_pos(self, variable: str) -> bool:
        return self.variable == variable and self.polarity is True

    def is_neg(self, variable: str) -> bool:
        return self.variable == variable and self.polarity is False

    @staticmethod
    def make_pos(variable: str):
        return BoolLiteral(variable, True)

    @staticmethod
    def make_neg(variable: str):
        return BoolLiteral(variable, False)

    def negate(self):
        return BoolLiteral(self.variable, not self.polarity)


class Clause:
    """
    A CNF clause (an OR of literals).
    """
    def __init__(self, *literals: BoolLiteral):
        # Store as a set: duplicates disappear automatically.
        self.literals: Set[BoolLiteral] = set(literals)

    def __repr__(self) -> str:
        return self.literals.__repr__()
    
    def __iter__(self):
        return iter(self.literals)
    
    def __eq__(self, other) -> bool:
        # Two clauses are equal if they have the same set of literals
        return isinstance(other, Clause) and self.literals == other.literals

    def __hash__(self) -> int:
        # Needed so Clause can be compared and stored in sets
        return hash(frozenset(self.literals))

    @staticmethod
    def make(*lit_strings: str) -> "Clause":
        """Convenience for small tests: Clause.make("1","-2","3")"""
        literals: List[BoolLiteral] = []
        for lit_string in lit_strings:
            if lit_string.startswith("-"):
                literals.append(BoolLiteral.make_neg(lit_string[1:]))
            else:
                literals.append(BoolLiteral.make_pos(lit_string))
        return Clause(*literals)

class ImplicationGraph:
    """Implication graph used during conflict analysis.

    Stored as: child -> set(parents)
    because explain() needs parents quickly.
    """
    def __init__(
        self,
        edges: Optional[Dict[BoolLiteral, Set[BoolLiteral]]] = None,
        conflict_clause: Optional[Set[BoolLiteral]] = None,
    ):
        self.edges: Dict[BoolLiteral, Set[BoolLiteral]] = edges if edges is not None else {}
        self.conflict_clause: Optional[Set[BoolLiteral]] = conflict_clause

    def add_node(self, node: BoolLiteral) -> None:
        self.edges.setdefault(node, set())

    def add_edge(self, src: BoolLiteral, tgt: BoolLiteral) -> None:
        self.edges.setdefault(tgt, set()).add(src)

    def add_conflict(self, srcs: Set[BoolLiteral]) -> None:
        self.conflict_clause = set(srcs)

    def explain(self, node: BoolLiteral) -> None:
        """One resolution-like step.

        - remove ¬node from conflict clause
        - add negations of node's parents
        """
        if self.conflict_clause is None:
            return

        self.conflict_clause.discard(node.negate())
        for parent in self.edges.get(node, set()):
            self.conflict_clause.add(parent.negate())

    def __repr__(self) -> str:
        out = []
        for tgt, srcs in self.edges.items():
            for src in srcs:
                out.append(f"{src!r} -> {tgt!r}")
        return "\n".join(out) + ("\n" if out else "")

    def __deepcopy__(self, memo):
        return ImplicationGraph(deepcopy(self.edges), deepcopy(self.conflict_clause))


class Model:
    """
    A variable assignment.
    """
    def __init__(self):
        self.assignment: List[BoolLiteral] = []
        self.decision_level: int = 0
        # decisions stores the assignment index where each decision level starts
        self.decisions: List[int] = []
        self.decision_levels: Dict[BoolLiteral, int] = {}

    def __contains__(self, literal: BoolLiteral) -> bool:
        return literal in self.assignment

    def assign(self, literal: BoolLiteral) -> None:
        # assign = forced (propagation)
        self.assignment.append(literal)
        self.decision_levels[literal] = self.decision_level

    def decide(self, literal: BoolLiteral) -> None:
        # decide = guess at a new decision level
        self.decisions.append(len(self.assignment))
        self.assignment.append(literal)
        self.decision_level += 1
        self.decision_levels[literal] = self.decision_level

    def backjump(self, decision_level: int) -> None:
        idx = self.decisions[decision_level]
        removed = self.assignment[idx:]

        self.assignment = self.assignment[:idx]
        self.decisions = self.decisions[:decision_level]
        self.decision_level = decision_level

        # Remove stale decision level mappings
        for lit in removed:
            self.decision_levels.pop(lit, None)

    def get_current_decision_literals(self) -> List[BoolLiteral]:
        if not self.decisions:
            return self.assignment
        return self.assignment[self.decisions[-1]:]

    def get_last_literal(self) -> BoolLiteral:
        return self.assignment[-1]

    # correctly checks both literal and its negation
    def get_level(self, literal: BoolLiteral) -> int:
        """IMPORTANT: learned clauses can contain ¬x even if the model stores x.

        So if literal isn't found, we also try its negation.
        """
        lvl = self.decision_levels.get(literal, None)
        if lvl is not None:
            return lvl
        return self.decision_levels.get(literal.negate(), -1)

    def __repr__(self) -> str:
        if self.decision_level == 0:
            return " ".join(repr(l) for l in self.assignment)

        out: List[str] = []
        last = 0
        for idx in self.decisions:
            out.extend(repr(l) for l in self.assignment[last:idx])
            out.append("•")
            last = idx
        out.extend(repr(l) for l in self.assignment[last:])
        return " ".join(out)

    def __iter__(self):
        return iter(self.assignment)


class State:
    """
    State for the CDCL proof system.
    """
    def __init__(self, clauses: List[Clause]):
        self.clauses = clauses
        self.model = Model()
        self.conflict = None
        self.unsat = False
        self.sat = False

    def __repr__(self) -> str:
        if self.unsat:
            return "UNSAT"
        if self.sat:
            return "SAT"
        
        out = []
        out.append("Δ = " + repr(self.clauses))
        out.append("M = " + repr(self.model))
        out.append("C = " + (repr(self.conflict) if self.conflict else "no"))
        return "\n".join(out) + "\n"


class Core:
    """ 
    Implements the core CDCL-style rules on the current State.
    """
    def __init__(self, state: State):
        self.graphs: List[ImplicationGraph] = [ImplicationGraph()]
        self.graph: ImplicationGraph = self.graphs[-1]
        self.in_conflict: bool = False
        self.state = state

    def propagate(self, clause_idx: int) -> bool:
        """Unit propagation using clause_idx.
        Returns True if it made a new assignment.
        """
        clause = self.state.clauses[clause_idx]
        unassigned_lit: Optional[BoolLiteral] = None
        num_unassigned = 0

        for literal in clause:
            if literal.negate() not in self.state.model:
                num_unassigned += 1
                unassigned_lit = literal

        if num_unassigned == 1 and \
           unassigned_lit not in self.state.model and \
           unassigned_lit.negate() not in self.state.model:

            self.state.model.assign(unassigned_lit)
            self.graph.add_node(unassigned_lit)

            for literal in clause.literals - {unassigned_lit}:
                self.graph.add_edge(literal.negate(), unassigned_lit)

            return True
        return False

    def decide(self, literal: BoolLiteral) -> bool:
        """Make a decision assignment at a new decision level."""
        if literal not in self.state.model and literal.negate() not in self.state.model:
            self.state.model.decide(literal)
            self.graphs.append(deepcopy(self.graph))
            self.graph = self.graphs[-1]
            return True
        return False

    def conflict(self, clause_idx: int) -> bool:
        """Detect a conflicting clause (all literals are false)."""
        if not self.in_conflict:
            clause = self.state.clauses[clause_idx]
            for literal in clause:
                if literal.negate() not in self.state.model:
                    return False
            self.in_conflict = True
            self.graph.add_conflict(clause.literals)
            # Clause(*set) unpacks the set into individual literals.
            # Without this fix, conflict analysis would crash or behave incorrectly.
            self.state.conflict = Clause(*self.graph.conflict_clause)
            return True
        return False

    def explain(self) -> bool:
        """Explain conflict until only 1 literal remains at current decision level."""
        decision_literals = self.state.model.get_current_decision_literals()
        while len(decision_literals) > 1:
            last_literal = self.state.model.assignment.pop(-1)
            self.graph.explain(last_literal)
            decision_literals = decision_literals[:-1]
        return True

    def backjump(self, decision_level: int) -> bool:
        """Backjump to decision_level and assert the learned clause."""
        if not self.in_conflict or self.graph.conflict_clause is None:
            return False

        conflict_clause = self.graph.conflict_clause
        decision_literal = self.state.model.get_last_literal()
        uip_neg = decision_literal.negate()

        # IMPORTANT: conflict_clause contains uip_neg (not decision_literal)
        level = -1
        for literal in conflict_clause - {uip_neg}:
            level = max(level, self.state.model.get_level(literal))

        if decision_level >= level:
            self.in_conflict = False
            self.state.model.backjump(decision_level)

            # Assert the negation of the remaining literal.
            self.state.model.assign(decision_literal.negate())

            self.state.conflict = None
            self.graphs = self.graphs[: decision_level + 1]
            self.graph = self.graphs[-1]
            return True
        return False

    def fail(self) -> bool:
        """UNSAT if we are in conflict at decision level 0."""
        if self.state.model.decision_level == 0 and self.in_conflict:
            self.state.unsat = True
            return True
        return False

    def learn(self) -> Optional[Clause]:
        """Add the current conflict clause to the clause database (if new)."""
        if self.graph.conflict_clause is None:
            return None

        learned = Clause(*self.graph.conflict_clause)
        if learned not in self.state.clauses:
            self.state.clauses.append(learned)
        return learned

    # TODO: store a map T[n] = {clause indices} such that if C = clause[k], k in T[n], then C has n literals x s.t. x, ~x are both unassigned

    def __repr__(self) -> str:
        core_string = 'State:\n' + repr(self.state)
        core_string += 'Implication Graph:\n' + repr(self.graph)
        return core_string