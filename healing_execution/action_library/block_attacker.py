import requests
import json
import time

RYU_REST_URL = "http://localhost:8080"
ATTACKER_MAC = "00:00:00:00:00:01" # Hardcoded H1 for demo

def block_attacker():
    """
    Blocks the attacker (H1) by installing a high-priority DROP rule on all switches.
    This is a REAL action that checks for switch dpid 1 (s1) usually connected to H1.
    """
    print("[ACTION] BLocking Host: H1 (MAC: 00:00:00:00:00:01)")
    print("[ACTION] Converting Simulation to REALITY...")
    
    # We will install this rule on Switch 1 (dpid=1) because that's where H1 is connected
    dpid = 1
    
    url = f"{RYU_REST_URL}/stats/flowentry/add"
    
    # OpenFlow Match: Ethernet Source Address = Attacker MAC
    # Action: [] (Empty list means DROP)
    payload = {
        "dpid": dpid,
        "cookie": 1,
        "cookie_mask": 1,
        "table_id": 0,
        "idle_timeout": 30, # Block for 30 seconds then auto-expire
        "hard_timeout": 30,
        "priority": 100,    # Higher priority than default forwarding
        "flags": 1,
        "match": {
            "eth_src": ATTACKER_MAC
        },
        "actions": []       # DROP
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"[SUCCESS] installed DROP rule for {ATTACKER_MAC} on Switch {dpid}")
            print("[INFO] Traffic from H1 is now BLOCKED for 30 seconds.")
        else:
            print(f"[ERROR] Failed to install drop rule: {response.text}")
    except Exception as e:
        print(f"[ERROR] Could not connect to Controller: {e}")
