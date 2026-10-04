import urllib.request
import json
import time
import sys
import argparse

def get_recent_runs(limit=5):
    url = f'https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs?per_page={limit}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data.get('workflow_runs', [])

def get_run_jobs(run_id):
    url = f'https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs/{run_id}/jobs'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data.get('jobs', [])

def check_runs(wait=False, timeout_sec=180, verbose=False):
    start_time = time.time()
    print("🤖 Automated GitHub Actions Status Monitor")
    print("=" * 60)
    
    while True:
        try:
            runs = get_recent_runs(limit=5)
        except Exception as e:
            print(f"Error requesting GitHub API: {e}")
            if not wait:
                return 1
            time.sleep(10)
            continue
            
        active_runs = [r for r in runs if r.get('status') in ['queued', 'in_progress', 'requested', 'waiting']]
        
        if not active_runs or not wait:
            print(f"\nStatus Report (at {time.strftime('%H:%M:%S IST')}):")
            print("-" * 60)
            has_failure = False
            
            for r in runs[:3]:
                r_id = r.get('id')
                r_num = r.get('run_number')
                name = r.get('name')
                status = r.get('status')
                conc = r.get('conclusion') or 'running...'
                msg = r.get('head_commit', {}).get('message', '').split('\n')[0]
                icon = "✅" if conc == "success" else ("❌" if conc == "failure" else "⏳")
                
                print(f"{icon} Run #{r_num} ({r_id}): {name}")
                print(f"   Status: {status} | Conclusion: {conc}")
                print(f"   Commit: {msg}")
                
                if conc == "failure":
                    has_failure = True
                    
                if verbose or conc == "failure":
                    try:
                        jobs = get_run_jobs(r_id)
                        for j in jobs:
                            j_icon = "  ✓" if j.get('conclusion') == 'success' else "  ✗"
                            print(f"   {j_icon} Job: {j.get('name')} -> {j.get('conclusion')}")
                            for s in j.get('steps', []):
                                if s.get('conclusion') == 'failure' or verbose:
                                    s_icon = "    ✓" if s.get('conclusion') == 'success' else "    ✗"
                                    print(f"     {s_icon} Step: {s.get('name')} -> {s.get('conclusion')}")
                    except Exception as je:
                        print(f"   Could not fetch job details: {je}")
                print("-" * 60)
                
            if active_runs and wait:
                print(f"⏳ Waiting for {len(active_runs)} active workflow run(s) to finish...")
            else:
                return 1 if has_failure else 0
                
        elapsed = time.time() - start_time
        if elapsed >= timeout_sec:
            print(f"⚠️ Timeout of {timeout_sec}s reached while waiting for workflow completion.")
            return 1
            
        sys.stdout.write(f"\r⏳ Polling GitHub API... ({int(elapsed)}s elapsed)")
        sys.stdout.flush()
        time.sleep(8)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Check VedaVMS GitHub Actions workflow run status")
    parser.add_argument("--wait", action="store_true", help="Poll until active workflow runs complete")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds when waiting")
    parser.add_argument("--verbose", action="store_true", help="Print detailed job and step breakdown")
    args = parser.parse_args()
    
    sys.exit(check_runs(wait=args.wait, timeout_sec=args.timeout, verbose=args.verbose))
