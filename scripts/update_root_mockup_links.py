import glob
import re
import os

def update_root_mockup_links():
    mockup_files = glob.glob("mockup/*.html")
    for f in mockup_files:
        with open(f, "r", encoding="utf-8") as fh:
            c = fh.read()
        
        # Replace href="html_viewer.html" or href='html_viewer.html' with href="viewer/html_viewer.html"
        new_c = re.sub(r'href=(["\'])html_viewer\.html\1', r'href=\1viewer/html_viewer.html\1', c)
        
        if new_c != c:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new_c)
            print(f"Updated html_viewer links in {f}")
        else:
            print(f"No changes in {f}")

if __name__ == "__main__":
    update_root_mockup_links()
