# CDCL SAT Solver (Baseline vs VSIDS)

**Course:** CS257 – Introduction to Automated Reasoning  
**Project:** Option 1 – SAT decision procedure (CDCL + VSIDS)

**Team**
- Yash — (Stanford email)
- Bryce — (Stanford email)
- Oscar — (Stanford email)

---

## What this project does

We built a program that solves **SAT problems** written in **DIMACS CNF** format (`.cnf`).

- **SAT** means: “Can we set variables to True/False so all clauses are satisfied?”
- Our solver uses a CDCL-style loop (propagate → conflict? learn/backjump → decide).
- We compare two “guessing” methods:
  - **baseline**: choose a random unassigned literal
  - **vsids**: keep scores for literals and guess the highest-score one

---

## Requirements

- Python **3.9+**
- No extra Python packages needed

Check:
```bash
python --version

""""
Quick start: solve ONE CNF file

Baseline (random)
Bash
python main.py path/to/problem.cnf --heuristic baseline --timeout 10
VSIDS
Bash
python main.py path/to/problem.cnf --heuristic vsids --timeout 10
Help / all options
python main.py -h

What you’ll see printed
Status: SAT, UNSAT, or TIMEOUT
Runtime
Decisions, conflicts, learned clauses, propagations
(These are the numbers we compare for baseline vs VSIDS.)
""""

""""
Run MANY CNF files (evaluation harness)
If you have a folder of .cnf files:
python eval_harness.py path/to/cnf_folder --timeout 10 --out results.csv
This runs both baseline and VSIDS on each .cnf file and writes results.csv.

Run only VSIDS
Bash
python eval_harness.py path/to/cnf_folder --timeout 10 --no-baseline --out results_vsids.csv

Run only baseline
Bash
python eval_harness.py path/to/cnf_folder --timeout 10 --no-vsids --out results_baseline.csv
""""

Results CSV columns
Each row is one run: (file, heuristic)
Common columns:
status (SAT, UNSAT, TIMEOUT)
runtime_sec
decisions
conflicts
learned_clauses
propagations

Repo layout (what each file does)
parser.py
Reads DIMACS CNF (.cnf) and builds a list of clauses.
core.py
Core CDCL rules / state objects (propagate, conflict, explain, learn, backjump).
heuristics.py
Contains:
baseline heuristic (random)
VSIDS heuristic (bump + decay + choose max activity)
solver.py
The main solver loop that runs until SAT/UNSAT/TIMEOUT.
main.py
Command line entry point for solving one CNF file (baseline or vsids).
eval_harness.py
Runs many CNFs and saves a CSV.

Notes / limitations
This is a student implementation; large benchmarks may timeout.
If runtime becomes a problem, the next improvement would be faster propagation
(e.g., watched literals), but that is optional.


---

## The one change needed to make the README commands work

### Replace current `main.py` with this CLI version

```python
from __future__ import annotations

import argparse
from solver import solve_dimacs


def main() -> None:
    ap = argparse.ArgumentParser(description="CDCL SAT solver (baseline vs VSIDS)")
    ap.add_argument("cnf", help="Path to a DIMACS CNF file (.cnf)")
    ap.add_argument("--heuristic", choices=["baseline", "vsids"], default="baseline")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=0)

    # Optional VSIDS knobs (fine to leave defaults)
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