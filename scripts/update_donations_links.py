import glob

files = sorted(glob.glob('mockup/*.html') + glob.glob('build/*.html'))
for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update nav donate button
    new_content = content.replace('href="https://vedavms.in/Donations.html" target="_blank" class="donate-btn"', 'href="donations.html" class="donate-btn"')
    # Update footer donate link
    new_content = new_content.replace('href="https://vedavms.in/Donations.html" target="_blank"', 'href="donations.html"')
    # Any other remaining occurrences
    new_content = new_content.replace('href="https://vedavms.in/Donations.html"', 'href="donations.html"')

    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated donations link in {path}")
