import urllib.request
import json

url = 'https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs?per_page=10'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        for run in data.get('workflow_runs', []):
            print(f"ID: {run['id']} | Name: {run['name']} | Status: {run['status']} | Conclusion: {run['conclusion']} | Created: {run['created_at']}")
            print(f"   URL: {run['html_url']}")
except Exception as e:
    print('Error:', e)
