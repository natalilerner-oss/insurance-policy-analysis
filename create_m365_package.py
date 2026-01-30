import zipfile
import os
import struct
import zlib

def create_dummy_png(filename, width, height):
    """Creates a minimal valid PNG file."""
    # PNG Signature
    png_sig = b'\x89PNG\r\n\x1a\n'
    
    # IHDR Chunk
    ihdr_len = struct.pack('>I', 13)
    ihdr_type = b'IHDR'
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_type + ihdr_data) & 0xFFFFFFFF)
    
    # IDAT Chunk (minimal data)
    raw_data = b'\x00' * ((width * 3 + 1) * height) # simplistic, assuming RGB
    compressed_data = zlib.compress(raw_data)
    idat_len = struct.pack('>I', len(compressed_data))
    idat_type = b'IDAT'
    idat_crc = struct.pack('>I', zlib.crc32(idat_type + compressed_data) & 0xFFFFFFFF)
    
    # IEND Chunk
    iend_len = struct.pack('>I', 0)
    iend_type = b'IEND'
    iend_crc = struct.pack('>I', zlib.crc32(iend_type) & 0xFFFFFFFF)
    
    with open(filename, 'wb') as f:
        f.write(png_sig)
        f.write(ihdr_len + ihdr_type + ihdr_data + ihdr_crc)
        f.write(idat_len + idat_type + compressed_data + idat_crc)
        f.write(iend_len + iend_type + iend_crc)

def create_m365_package():
    base_dir = '/workspaces/insurance-policy-analysis/m365-agent'
    output_zip = '/workspaces/insurance-policy-analysis/insurance-agent-app.zip'
    
    # Create dummy icons if they are empty
    color_icon = os.path.join(base_dir, 'color.png')
    outline_icon = os.path.join(base_dir, 'outline.png')
    
    if os.path.exists(color_icon) and os.path.getsize(color_icon) == 0:
        print("Creating dummy color.png...")
        create_dummy_png(color_icon, 192, 192) # Standard size for color
        
    if os.path.exists(outline_icon) and os.path.getsize(outline_icon) == 0:
        print("Creating dummy outline.png...")
        create_dummy_png(outline_icon, 32, 32) # Standard size for outline

    files_to_include = [
        'manifest.json',
        'color.png',
        'outline.png',
        'openapi.yaml',
        'instructions.md'
    ]
    
    print(f"Creating {output_zip}...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files_to_include:
            file_path = os.path.join(base_dir, file)
            if os.path.exists(file_path):
                print(f"  Adding {file}")
                zf.write(file_path, arcname=file)
            else:
                print(f"  WARNING: {file} not found!")

if __name__ == '__main__':
    create_m365_package()
