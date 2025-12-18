def compute_availability(total_time, downtime):
    if total_time == 0:
        return 1.0
    return (total_time - downtime) / total_time
