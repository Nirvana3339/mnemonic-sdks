"""Smoke test: pip install mnemo, then capture + recall once."""
import os
import time

from mnemo import Mnemo

API_KEY = os.environ["MNEMO_API_KEY"]
BASE = os.environ.get("MNEMO_BASE_URL", "http://localhost:8001/api")

with Mnemo(api_key=API_KEY, base_url=BASE) as m:
    agents = m.list_agents()
    if agents:
        agent_id = agents[0]["id"]
    else:
        agent_id = m.create_agent("demo-agent", name="Demo Agent")["id"]

    print("Capturing event...")
    res = m.capture(
        agent_id=agent_id,
        task="Add jitter to exponential backoff retry policy",
        actions=[{"type": "edit_file", "target": "retry.py", "result": "added jitter"}],
        output="Added 0.1s ± 50% jitter to backoff schedule",
        success=True,
        time_taken=1800,
        retries=0,
    )
    print(res)

    print("Waiting 12s for reflection...")
    time.sleep(12)

    print("Recall:")
    ctx = m.recall(agent_id=agent_id, task="retry transient 502", as_prompt=True)
    print(ctx)
