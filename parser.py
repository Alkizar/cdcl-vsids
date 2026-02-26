"""DIMACS CNF parser.

Clauses can be split across multiple lines, so we read tokens until we hit 0.
"""
from __future__ import annotations
from typing import List
from core import Clause, BoolLiteral


def parse_dimacs(path: str) -> List[Clause]:
    clauses: List[Clause] = []
    current_lits: List[BoolLiteral] = []

    with open(path, "r") as f:
        for raw_line in f:
            line = raw_line.strip()

            # Skip comments / problem line / empty lines
            if not line or line.startswith("c") or line.startswith("p"):
                continue

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

    return clauses