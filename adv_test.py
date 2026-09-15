import json, urllib.request, time
# Login first
data = json.dumps({"username": "admin", "password": "Test123!@#"}).encode()
req = urllib.request.Request("http://localhost:8000/login", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
cookie = resp.headers.get("Set-Cookie").split(";")[0]

# Poll the UAT task
task_id = "c8c3c983"
dup_check = []
for i in range(30):
    req2 = urllib.request.Request("http://localhost:8000/api/assessment/status/" + task_id)
    req2.add_header("Cookie", cookie)
    try:
        resp2 = urllib.request.urlopen(req2)
        d = json.loads(resp2.read().decode())
        logs = d.get("logs", [])
        status = d.get("status", "unknown")
        unique = set(logs)
        dups = len(logs) - len(unique)
        dup_check.append({"poll": i, "status": status, "logs": len(logs), "dups": dups, "progress": d.get("progress", 0)})
        if status in ["completed", "failed", "cancelled"]:
            break
    except Exception as e:
        print("Error:", e)
    time.sleep(1)

print("Poll results:")
for r in dup_check:
    print("  Poll %d: status=%s, logs=%d, dups=%d, progress=%d%%" % (r["poll"], r["status"], r["logs"], r["dups"], r["progress"]))
max_dups = max(r["dups"] for r in dup_check) if dup_check else 0
print("Max duplicates across all polls: %d" % max_dups)
final = dup_check[-1] if dup_check else None
print("Final: %s" % final)