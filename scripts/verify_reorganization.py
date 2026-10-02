import os
import glob
import re

def verify_site_links():
    build_dir = "build"
    html_files = []
    for root, _, files in os.walk(build_dir):
        for f in files:
            if f.endswith(".html"):
                html_files.append(os.path.join(root, f))
    
    print(f"Verifying {len(html_files)} HTML files in {build_dir}...")
    errors = []
    
    for hf in html_files:
        hf_rel = os.path.relpath(hf, build_dir).replace("\\", "/")
        with open(hf, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check footer timestamp
        if "Generated:" not in content and not any(k in hf for k in ["docs_", "taittiriya_", "udaka_", "shanti_", "siva_"]):
            print(f"  Warning: No timestamp in {hf_rel}")
            
        # Find internal href links (excluding http, https, mailto, tel, javascript, #anchor)
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', content)
        for link in hrefs:
            if link.startswith(("http://", "https://", "mailto:", "tel:", "javascript:", "#")):
                continue
            
            # Split off hash or query parameters
            clean_link = link.split("#")[0].split("?")[0]
            if not clean_link:
                continue
            
            # Resolve relative to current file's directory
            dir_of_file = os.path.dirname(hf)
            resolved_path = os.path.normpath(os.path.join(dir_of_file, clean_link))
            
            if not os.path.exists(resolved_path):
                errors.append(f"Broken Link in {hf_rel}: href='{link}' -> unresolved target: {resolved_path}")

    if errors:
        print(f"\n[FAILED] Found {len(errors)} broken links:")
        for err in errors:
            print("  -", err)
        return False
    else:
        print("\n[PASSED] All internal links across build/ and build/viewer/ resolved successfully!")
        return True

if __name__ == "__main__":
    success = verify_site_links()
    if not success:
        exit(1)
