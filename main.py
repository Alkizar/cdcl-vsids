"""Run the solver on one DIMACS CNF file."""

from __future__ import annotations

import argparse
from solver import solve_dimacs


def main() -> None:
    ap = argparse.ArgumentParser(description="CDCL SAT solver")
    ap.add_argument("cnf", help="Path to a DIMACS CNF file")
    ap.add_argument("--heuristic", choices=["baseline", "vsids"], default="baseline")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=0)

    ap.add_argument("--vsids-bump", type=float, default=1.0)
    ap.add_argument("--vsids-decay", type=float, default=0.95)
    ap.add_argument("--vsids-decay-period", type=int, default=50)

    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    result = solve_dimacs(
        args.cnf,
        heuristic_name=args.heuristic,
        timeout_sec=args.timeout,
        seed=args.seed,
        vsids_bump=args.vsids_bump,
        vsids_decay_factor=args.vsids_decay,
        vsids_decay_period=args.vsids_decay_period,
        debug=args.debug,
    )

    print("\n=== RESULT ===")
    print("Status:", result.status)
    print("Runtime (sec):", round(result.runtime_sec, 6))
    print("Decisions:", result.stats.decisions)
    print("Conflicts:", result.stats.conflicts)
    print("Learned clauses:", result.stats.learned_clauses)
    print("Propagations:", result.stats.propagations)

    if result.status == "SAT":
        print("Assignment:")
        for v, val in sorted(result.assignment.items()):
            print(f"  {v} = {val}")


if __name__ == "__main__":
    main()