import json, urllib.request
data = json.dumps({"username": "admin", "password": "Test123!@#"}).encode()
req = urllib.request.Request("http://localhost:8000/login", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
cookie = resp.headers.get("Set-Cookie").split(";")[0]
req2 = urllib.request.Request("http://localhost:8000/api/tasks/list")
req2.add_header("Cookie", cookie)
resp2 = urllib.request.urlopen(req2)
d = json.loads(resp2.read().decode())
for t in d.get("tasks", []):
    tid = t.get("id")
    status = t.get("status")
    name = t.get("name")
    print("Task: %s, status: %s, name: %s" % (tid, status, name))
    # Get logs for this task
    try:
        req3 = urllib.request.Request("http://localhost:8000/api/assessment/status/" + tid)
        req3.add_header("Cookie", cookie)
        resp3 = urllib.request.urlopen(req3)
        td = json.loads(resp3.read().decode())
        logs = td.get("logs", [])
        unique = set(logs)
        dups = len(logs) - len(unique)
        print("  Logs: %d, Unique: %d, Duplicates: %d" % (len(logs), len(unique), dups))
        if dups > 0:
            print("  WARNING: Duplicate log entries found!")
    except Exception as e:
        print("  Error getting logs: %s" % e)