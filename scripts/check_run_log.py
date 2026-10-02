import urllib.request
import json

url = 'https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    
    staging_run = None
    for r in data.get('workflow_runs', []):
        if 'Staging' in r.get('name', ''):
            staging_run = r
            break
            
    if staging_run:
        print(f"Staging Run #{staging_run['run_number']} (ID: {staging_run['id']})")
        print(f"Status: {staging_run['status']} | Conclusion: {staging_run['conclusion']}")
        
        jobs_url = staging_run['jobs_url']
        req_jobs = urllib.request.Request(jobs_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_jobs, timeout=10) as resp_jobs:
            jobs_data = json.loads(resp_jobs.read().decode('utf-8'))
            for j in jobs_data.get('jobs', []):
                print(f"Job: {j['name']} ({j['conclusion']})")
                for s in j.get('steps', []):
                    print(f"  Step: {s['name']} -> {s['conclusion']}")
except Exception as e:
    print("Error:", e)
