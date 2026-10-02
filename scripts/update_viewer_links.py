import glob
import re
import os

def update_viewer_links():
    # Fix html_viewer.html and index.html in mockup/viewer
    for f in ['mockup/viewer/html_viewer.html', 'mockup/viewer/index.html']:
        if not os.path.exists(f):
            continue
        with open(f, 'r', encoding='utf-8') as fh:
            c = fh.read()
        
        for page in ['index.html', 'documents.html', 'videos.html', 'articles.html', 'convention.html', 'about.html', 'donations.html']:
            c = re.sub(r'href=(["\'])' + re.escape(page) + r'\1', r'href=\1../' + page + r'\1', c)
        
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(c)
        print(f"Updated links in {f}")

    # Fix reader files in mockup/viewer
    for p in glob.glob('mockup/viewer/*.html'):
        if 'html_viewer' in p or p.endswith('index.html'):
            continue
        with open(p, 'r', encoding='utf-8') as fh:
            c = fh.read()
        c = re.sub(r'href=(["\'])index\.html\1', r'href=\1../index.html\1', c)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(c)
        print(f"Updated back link in reader: {p}")

if __name__ == '__main__':
    update_viewer_links()
