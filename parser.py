"""DIMACS CNF parser.

Clauses can be split across multiple lines, so we read tokens until we hit 0.
"""
from __future__ import annotations
from typing import List
from core import Clause, BoolLiteral


def parse_dimacs(path: str) -> List[Clause]:
    clauses: List[Clause] = []
    current_lits: List[BoolLiteral] = []
    expected_clauses: Optional[int] = None
    expected_vars: Optional[int] = None


    with open(path, "r") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("c"):
                continue
            
            if line.startswith("p"):
                parts = line.split()
                if len(parts) >= 4 and parts[1].lower() == "cnf":
                    expected_vars = int(parts[2])
                    expected_clauses = int(parts[3])
                continue

            if line.startswith("%"):
                break

            for tok in line.split():
                if tok == "0":
                    # End of this clause
                    if current_lits:
                        clauses.append(Clause(*current_lits))
                        current_lits = []
                    continue

                if tok.startswith("-"):
                    current_lits.append(BoolLiteral.make_neg(tok[1:]))
                else:
                    current_lits.append(BoolLiteral.make_pos(tok))

    # If the file forgot a trailing 0, still keep the last clause.
    if current_lits:
        clauses.append(Clause(*current_lits))

    if expected_clauses is not None:
        if len(clauses) != expected_clauses:
            raise ValueError(
                f"p cnf says {expected_clauses} clauses, got {len(clauses)}"
            )
    if expected_vars is not None:
        vars_seen = {lit.variable for c in clauses for lit in c}
        if not all(1 <= int(v) <= expected_vars for v in vars_seen):
            raise ValueError(f"variable(s) out of range [1, {expected_vars}]")

    return clauses