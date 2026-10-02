import json
import urllib.request

url = "https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs/37002773229/jobs"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

for job in data.get("jobs", []):
    print(f"Job: {job['name']} ({job['conclusion']})")
    for step in job.get("steps", []):
        print(f"  Step: {step['name']} -> {step['conclusion']}")
