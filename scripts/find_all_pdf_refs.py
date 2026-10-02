import os
import re
from urllib.parse import urlparse, unquote

def find_all_pdf_references():
    pdf_refs = set()
    file_sources = {}
    
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.cache' in root:
            continue
        for f in files:
            if f.endswith(('.html', '.php', '.js', '.json', '.txt', '.md', '.csv', '.py')):
                path = os.path.join(root, f)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                    
                    # Pattern for relative and absolute URLs
                    urls = re.findall(r'(https?://(?:www\.)?vedavms\.in/[^\s"\'()<>]+\.pdf)', content, re.I)
                    for u in urls:
                        clean_u = u.split('?')[0].split('#')[0].rstrip('.,;')
                        pdf_refs.add(clean_u)
                        file_sources.setdefault(clean_u, set()).add(path)
                        
                    rel_urls = re.findall(r'href=["\'](/?[a-zA-Z0-9_\-\./%]+\.pdf)["\']', content, re.I)
                    for r in rel_urls:
                        if not r.startswith('http'):
                            full = f"https://vedavms.in/{r.lstrip('/')}"
                            pdf_refs.add(full)
                            file_sources.setdefault(full, set()).add(path)
                except Exception:
                    pass
                    
    return pdf_refs, file_sources

if __name__ == '__main__':
    refs, sources = find_all_pdf_references()
    print(f"Discovered {len(refs)} unique PDF references in repo.")
