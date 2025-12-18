import json
import matplotlib.pyplot as plt

from evaluation_analytics.metrics.mttr import compute_mttr
from evaluation_analytics.metrics.mttd import compute_mttd
from evaluation_analytics.metrics.availability import compute_availability
from evaluation_analytics.metrics.recovery_efficiency import compute_recovery_efficiency

BASELINE_FILE = "evaluation_analytics/benchmarks/baseline.json"
OUTPUT_FILE = "evaluation_analytics/benchmarks/self_healing.json"


def run_analysis():

    mttr = compute_mttr()
    mttd = compute_mttd()

    total_time = 100.0      # simulated experiment duration
    failure_count = 5
    downtime = mttr * failure_count

    availability = compute_availability(total_time, downtime)

    with open(BASELINE_FILE) as f:
        baseline = json.load(f)

    recovery_eff = compute_recovery_efficiency(mttr, baseline["mttr"])

    results = {
        "MTTD": round(mttd, 2),
        "MTTR": round(mttr, 2),
        "Availability": round(availability, 3),
        "RecoveryEfficiency": round(recovery_eff, 2)
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n[PERFORMANCE ANALYSIS RESULTS]")
    for k, v in results.items():
        print(f"{k}: {v}")

    generate_plots(baseline, results)


def generate_plots(baseline, results):

    # MTTR Comparison Plot
    plt.figure()
    plt.bar(
        ["Baseline", "Self-Healing"],
        [baseline["mttr"], results["MTTR"]]
    )
    plt.ylabel("Seconds")
    plt.title("MTTR Comparison")
    plt.savefig("evaluation_analytics/plots/mttr_comparison.png")

    # Availability Comparison Plot
    plt.figure()
    plt.bar(
        ["Baseline", "Self-Healing"],
        [baseline["availability"], results["Availability"]]
    )
    plt.title("Availability Comparison")
    plt.savefig("evaluation_analytics/plots/availability_plot.png")


if __name__ == "__main__":
    run_analysis()
