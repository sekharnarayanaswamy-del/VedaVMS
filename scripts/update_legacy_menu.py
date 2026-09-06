import re
import difflib

def update_donations():
    with open("original_Donations.html", "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pattern = r'(<li><a href="English_Videos\.html">English Videos</a></li>\s*)<li class="last"><a href="contact\.html"><span>Contacts</span></a>\s*</li>'
    replacement = r'<li class="last"><a href="English_Videos.html">English Videos</a></li>'
    
    assert re.search(pattern, content), "Pattern not found in original_Donations.html"
    updated = re.sub(pattern, replacement, content, count=1)
    
    with open("Donations.html", "w", encoding="utf-8") as f:
        f.write(updated)
    
    print("Donations.html updated successfully.")
    diff = list(difflib.unified_diff(content.splitlines(), updated.splitlines(), lineterm=""))
    print("\n".join(diff[:25]))

def update_index():
    with open("original_index.html", "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    pattern = r'(<li><a href="English_Videos\.html">English Videos</a></li>\s*)<li class="last"><a href="contact\.html"><span>Contacts</span></a>\s*</li>'
    replacement = r'<li class="last"><a href="English_Videos.html">English Videos</a></li>'
    
    assert re.search(pattern, content), "Pattern not found in original_index.html"
    updated = re.sub(pattern, replacement, content, count=1)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(updated)
    
    print("\nindex.html updated successfully.")
    diff = list(difflib.unified_diff(content.splitlines(), updated.splitlines(), lineterm=""))
    print("\n".join(diff[:25]))

if __name__ == "__main__":
    update_donations()
    update_index()
