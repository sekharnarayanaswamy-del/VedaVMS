import urllib.request
import json

url = 'https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs?per_page=5'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    print("Recent GitHub Actions Runs:")
    for run in data.get('workflow_runs', []):
        msg = run.get('head_commit', {}).get('message', '').split('\n')[0]
        print(f"  Run #{run.get('run_number')}: {run.get('name')} | Status: {run.get('status')} | Conclusion: {run.get('conclusion')} | Commit: {msg}")
except Exception as e:
    print("API request error:", e)
