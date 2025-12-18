import time
from .state_store import LAST_ACTION_TIME

def is_in_cooldown(fault, cooldown):
    now = time.time()
    last_time = LAST_ACTION_TIME.get(fault, 0)

    if now - last_time < cooldown:
        return True

    LAST_ACTION_TIME[fault] = now
    return False
