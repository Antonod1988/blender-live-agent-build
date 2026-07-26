"""Poll a Blender bridge job until it leaves the running/queued state."""
import json
import sys
import time

from bl import send

job_id = sys.argv[1]
deadline = time.time() + float(sys.argv[2] if len(sys.argv) > 2 else 3000)
while time.time() < deadline:
    r = send("job.status", {"job_id": job_id}, 30)
    st = r.get("result", {}).get("status")
    if st not in ("queued", "running"):
        print(json.dumps(r, ensure_ascii=False)[:4000])
        break
    time.sleep(10)
else:
    print("TIMEOUT waiting for", job_id)
