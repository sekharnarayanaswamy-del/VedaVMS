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

def get_failed_step_reason(run_id):
    url = f'https://api.github.com/repos/sekharnarayanaswamy-del/VedaVMS/actions/runs/{run_id}/jobs'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for j in data.get('jobs', []):
                if j.get('conclusion') == 'failure':
                    for s in j.get('steps', []):
                        if s.get('conclusion') == 'failure':
                            return f"Job '{j.get('name')}' failed at step '{s.get('name')}'"
                    return f"Job '{j.get('name')}' failed"
    except Exception:
        pass
    return "Unknown failure reason"

def check_runs(wait=False, timeout_sec=180, verbose=False):
    start_time = time.time()
    
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
            print("🤖 GitHub Actions Status Monitor")
            print("=" * 60)
            has_failure = False
            
            for r in runs[:3]:
                name = r.get('name')
                conc = r.get('conclusion') or r.get('status') or 'running...'
                msg = r.get('head_commit', {}).get('message', '').split('\n')[0]
                
                if conc == "success":
                    print(f"✅ {name} — SUCCESS")
                elif conc == "failure":
                    has_failure = True
                    reason = get_failed_step_reason(r.get('id'))
                    print(f"❌ {name} — FAILED ({reason})")
                    print(f"   Commit: {msg}")
                else:
                    print(f"⏳ {name} — {conc.upper()}")
                    
                if verbose and conc != "failure":
                    print(f"   Commit: {msg}")
                    
            print("=" * 60)
            
            if active_runs and wait:
                print(f"⏳ Waiting for active workflow(s) to finish...")
            else:
                return 1 if has_failure else 0
                
        elapsed = time.time() - start_time
        if elapsed >= timeout_sec:
            print(f"\n⚠️ Timeout of {timeout_sec}s reached while waiting for workflow completion.")
            return 1
            
        sys.stdout.write(f"\r⏳ Polling GitHub Actions... ({int(elapsed)}s elapsed)")
        sys.stdout.flush()
        time.sleep(8)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Check VedaVMS GitHub Actions workflow run status")
    parser.add_argument("--wait", action="store_true", help="Poll until active workflow runs complete")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds when waiting")
    parser.add_argument("--verbose", action="store_true", help="Print commit messages on success")
    args = parser.parse_args()
    
    sys.exit(check_runs(wait=args.wait, timeout_sec=args.timeout, verbose=args.verbose))
