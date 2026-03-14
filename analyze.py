
def init_results():
    return {
        "number_timeouts"       : 0,
        "mean_runtime"          : 0.0,
        "mean_decisions"        : 0,
        "mean_conflicts"        : 0,
        "mean_learned_clauses"  : 0,
        "mean_propagations"     : 0,
        "last_runtime"          : 0.0,
    }

if __name__ == "__main__":

    results = {
        "baseline": init_results(),
        "vsids":    init_results(),
    }

    num_tests = 0
    max_runtime_diff_vsids = 0.0
    max_runtime_diff_baseline = 0.0

    with open("results-aim.csv", "r") as f:
        for raw_line in f:
            num_tests += 1

            if num_tests == 1:
                continue

            line = raw_line.strip().split(",")

            file_name       = line[0]
            file_path       = line[1]
            heuristic       = line[2]
            status          = line[3]
            runtime         = line[4]
            decisions       = line[5]
            conflicts       = line[6]
            learned_clauses = line[7]
            propagations    = line[8]

            if status == "TIMEOUT":
                results[heuristic]["number_timeouts"] += 1
            results[heuristic]["mean_runtime"]          += float(runtime)
            results[heuristic]["mean_decisions"]        += int(decisions)
            results[heuristic]["mean_conflicts"]        += int(conflicts)
            results[heuristic]["mean_learned_clauses"]  += int(learned_clauses)
            results[heuristic]["mean_propagations"]     += int(propagations)
            results[heuristic]["last_runtime"]          =  float(runtime)

            if heuristic == "vsids":
                max_runtime_diff_vsids = max(max_runtime_diff_vsids, results["vsids"]["last_runtime"] - results["baseline"]["last_runtime"])
                max_runtime_diff_baseline = max(max_runtime_diff_baseline, results["baseline"]["last_runtime"] - results["vsids"]["last_runtime"])

    num_tests = (num_tests - 1) // 2

    print(f"Analysis for {file_name.split('-')[0]}")
    print(f"Number of CNF formulas in benchmark: {num_tests}")
    print(f"Maximum runtime difference (VSIDS - baseline): {max_runtime_diff_vsids}")
    print(f"Maximum runtime difference (baseline - VSIDS): {max_runtime_diff_baseline}")

    for heuristic in results.keys():
        results[heuristic]["mean_runtime"]          /= num_tests
        results[heuristic]["mean_decisions"]        /= num_tests
        results[heuristic]["mean_conflicts"]        /= num_tests
        results[heuristic]["mean_learned_clauses"]  /= num_tests
        results[heuristic]["mean_propagations"]     /= num_tests

        # Show analysis
        print("------------")
        print(heuristic)
        for key in results[heuristic].keys():
            print(f"  {key}: {results[heuristic][key]}")
        print("------------")