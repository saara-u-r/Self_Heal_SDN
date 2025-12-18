#Used when flows are corrupted or inconsistent
import requests

RYU_REST_URL = "http://localhost:8080"

def reset_all_flows():
    """
    Clears all flow tables from switches
    """

    print("[ACTION] Resetting all flow tables...")

    try:
        response = requests.delete(f"{RYU_REST_URL}/stats/flowentry/clear/1")
        if response.status_code == 200:
            print("[ACTION] Flow tables cleared")
        else:
            print("[ERROR] Failed to clear flows")

    except Exception as e:
        print("[ERROR]", e)
