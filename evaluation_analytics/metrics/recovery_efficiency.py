def compute_recovery_efficiency(mttr, baseline_mttr):
    if baseline_mttr == 0:
        return 1.0
    return baseline_mttr / mttr
