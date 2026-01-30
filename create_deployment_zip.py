#!/usr/bin/env python3
"""
Create deployment zip file for Azure Functions
"""
import os
import zipfile
from pathlib import Path

def create_deployment_zip():
    """Create a deployment-ready zip file"""
    
    # Files and directories to include
    items_to_include = [
        'function_app.py',
        'host.json',
        'requirements.txt',
        'src/'
    ]
    
    # Patterns to exclude
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.git',
        'test_',
        '.pytest_cache'
    ]
    
    zip_filename = 'insurance-policy-api-deployment.zip'
    
    print(f"Creating deployment package: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for item in items_to_include:
            if os.path.isfile(item):
                # Add single file
                print(f"  Adding file: {item}")
                zipf.write(item)
            elif os.path.isdir(item):
                # Add directory recursively
                for root, dirs, files in os.walk(item):
                    # Skip excluded directories
                    dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                    
                    for file in files:
                        # Skip excluded files
                        if any(pattern in file for pattern in exclude_patterns):
                            continue
                        
                        file_path = os.path.join(root, file)
                        arc_name = file_path
                        print(f"  Adding: {arc_name}")
                        zipf.write(file_path, arc_name)
    
    # Get file size
    size_bytes = os.path.getsize(zip_filename)
    size_mb = size_bytes / (1024 * 1024)
    
    print(f"\n✅ Deployment package created successfully!")
    print(f"📦 File: {zip_filename}")
    print(f"📏 Size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
    
    # List contents
    print(f"\n📋 Package contents:")
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        file_list = zipf.namelist()
        print(f"   Total files: {len(file_list)}")
        for name in sorted(file_list)[:10]:
            print(f"   - {name}")
        if len(file_list) > 10:
            print(f"   ... and {len(file_list) - 10} more files")
    
    return zip_filename

if __name__ == '__main__':
    create_deployment_zip()
