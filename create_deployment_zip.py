#!/usr/bin/env python3
import os
import sys
import zipfile

os.chdir('/workspaces/insurance-policy-analysis')

zip_filename = 'insurance-policy-api-deployment.zip'
print(f"Creating {zip_filename}...")

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add main files
    zipf.write('function_app.py')
    zipf.write('host.json')
    zipf.write('requirements.txt')
    print(f"Added: function_app.py, host.json, requirements.txt")
    
    # Add src directory
    for root, dirs, files in os.walk('src'):
        # Remove __pycache__ from dirs to skip it
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
        
        for file in files:
            if not file.endswith('.pyc'):
                filepath = os.path.join(root, file)
                zipf.write(filepath)
                print(f"Added: {filepath}")

size = os.path.getsize(zip_filename)
print(f"\n✅ Created: {zip_filename}")
print(f"📏 Size: {size / 1024 / 1024:.2f} MB")

with zipfile.ZipFile(zip_filename, 'r') as zipf:
    print(f"📦 Contains {len(zipf.namelist())} files")
    
sys.exit(0)
