"""Evaluation harness: run many CNF files and save results.csv"""

from __future__ import annotations
import csv
import os
from typing import Dict, Iterable, List
from solver import SolveResult, solve_dimacs


def find_cnf_files(path: str) -> List[str]:
    """If path is a file -> [path]. If directory -> all *.cnf under it."""
    if os.path.isfile(path):
        return [path]

    cnfs: List[str] = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith(".cnf"):
                cnfs.append(os.path.join(root, f))
    cnfs.sort()
    return cnfs


def _result_to_row(cnf_path: str, heuristic: str, result: SolveResult) -> Dict[str, object]:
    return {
        "file": os.path.basename(cnf_path),
        "path": cnf_path,
        "heuristic": heuristic,
        "status": result.status,
        "runtime_sec": round(result.runtime_sec, 6),
        "decisions": result.stats.decisions,
        "conflicts": result.stats.conflicts,
        "learned_clauses": result.stats.learned_clauses,
        "propagations": result.stats.propagations,
    }


def run_benchmarks(
    cnf_files: Iterable[str],
    out_csv: str = "results.csv",
    timeout_sec: float = 10.0,
    seed: int = 0,
    run_baseline: bool = True,
    run_vsids: bool = True,
) -> None:
    heuristics: List[str] = []
    if run_baseline:
        heuristics.append("baseline")
    if run_vsids:
        heuristics.append("vsids")

    rows: List[Dict[str, object]] = []

    for cnf_path in cnf_files:
        for h in heuristics:
            result = solve_dimacs(
                cnf_path,
                heuristic_name=h,
                timeout_sec=timeout_sec,
                seed=seed,
            )
            row = _result_to_row(cnf_path, h, result)
            rows.append(row)

            print(
                f"[{h}] {os.path.basename(cnf_path)} -> {result.status} "
                f"({row['runtime_sec']}s, decisions={row['decisions']}, conflicts={row['conflicts']})"
            )

    fieldnames = list(rows[0].keys()) if rows else []
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"\nSaved results to: {out_csv}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Run CDCL solver benchmarks")
    ap.add_argument("path", help="A .cnf file or directory containing .cnf files")
    ap.add_argument("--out", default="results.csv")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("--no-vsids", action="store_true")
    args = ap.parse_args()

    cnfs = find_cnf_files(args.path)
    run_benchmarks(
        cnfs,
        out_csv=args.out,
        timeout_sec=args.timeout,
        seed=args.seed,
        run_baseline=not args.no_baseline,
        run_vsids=not args.no_vsids,
    )