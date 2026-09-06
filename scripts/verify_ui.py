import os
import re

files_to_check = [
    "mockup/index.html",
    "mockup/documents.html",
    "mockup/videos.html",
    "mockup/articles.html",
    "mockup/about.html",
    "mockup/convention.html",
    "build/index.html",
    "build/documents.html",
    "build/videos.html",
    "build/articles.html",
    "build/about.html",
    "build/convention.html",
]

print("=== VERIFYING SITE PAGES ===")
all_passed = True

for path in files_to_check:
    if not os.path.exists(path):
        print(f"[FAIL] Missing file: {path}")
        all_passed = False
        continue
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    has_nav_convention = 'href="convention.html"' in content
    has_footer_convention = ('convention.html' in content and 'footer' in content)
    has_title = '<title>' in content
    has_viewport = 'viewport' in content
    
    print(f"\nFile: {path} ({len(content):,} bytes)")
    print(f"  - Nav link to convention.html: {'OK' if has_nav_convention else 'MISSING'}")
    print(f"  - Footer link: {'OK' if has_footer_convention else 'MISSING'}")
    print(f"  - Responsive viewport meta: {'OK' if has_viewport else 'MISSING'}")

    if not (has_nav_convention and has_footer_convention and has_viewport):
        all_passed = False

print(f"\nOverall check result: {'ALL PASSED' if all_passed else 'SOME CHECKS FAILED'}")
