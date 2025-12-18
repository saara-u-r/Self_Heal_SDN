def enable_rate_limit():
    """
    Simulates enabling rate limiting on the controller to mitigate DoS.
    """
    print("[ACTION] Enabling rate limiting logic...")
    print("[ACTION] Installing Meter Table ID: 1 (Rate: 1000 pps)")
    # Real implementation would send a REST call to install an OpenFlow Meter
