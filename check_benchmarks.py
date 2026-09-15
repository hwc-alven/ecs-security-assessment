import json, os
base = "/opt/ecs-security-assessment/data/benchmarks"
for f in ["cis_linux.json", "stig_linux.json", "nist_linux.json", "pci_linux.json"]:
    path = os.path.join(base, f)
    with open(path) as fh:
        d = json.load(fh)
    controls = d.get("controls", [])
    print(f"{f}: platform={d.get('platform')}, version={d.get('version')}, controls={len(controls)}")
    if controls:
        c = controls[0]
        print(f"  Sample: id={c.get('id')}, title={c.get('title')[:60]}, severity={c.get('severity')}, category={c.get('category')}")
print("===TESTS===")
test_dir = "/opt/ecs-security-assessment/tests"
for item in os.listdir(test_dir):
    full = os.path.join(test_dir, item)
    print(f"  {item}: {'dir' if os.path.isdir(full) else 'file'}")
print("===KEYPAIR===")
kp_dir = "/opt/ecs-security-assessment/data/keypair"
for item in os.listdir(kp_dir):
    full = os.path.join(kp_dir, item)
    print(f"  {item}: {os.path.getsize(full)} bytes")