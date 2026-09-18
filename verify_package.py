"""
Verify upload package integrity.
Usage: python verify_package.py
"""
import json
import hashlib
import zlib
import struct
from pathlib import Path

def verify_package():
    base = Path(__file__).parent
    
    print("=" * 60)
    print("MusicToolkit Pro - Package Verification")
    print("=" * 60)
    
    # 1. Check manifest
    print("\n1. Checking manifest.json...")
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        print("   ✗ manifest.json not found!")
        return False
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    print(f"   ✓ Package version: {manifest['package_version']}")
    print(f"   ✓ Total genres: {manifest['database']['total_genres']}")
    
    # 2. Verify data.json
    print("\n2. Verifying data.json...")
    data_path = base / "data.json"
    if not data_path.exists():
        print("   ✗ data.json not found!")
        return False
    
    with open(data_path, "rb") as f:
        data_bytes = f.read()
    
    data_md5 = hashlib.md5(data_bytes).hexdigest()
    expected_md5 = manifest["database"]["data_md5"]
    
    if data_md5 == expected_md5:
        print(f"   ✓ MD5 checksum verified")
    else:
        print(f"   ✗ MD5 mismatch!")
        print(f"     Expected: {expected_md5}")
        print(f"     Got:      {data_md5}")
        return False
    
    # Validate JSON
    try:
        data = json.loads(data_bytes)
        print(f"   ✓ Valid JSON, {len(data['genres'])} genres")
    except Exception as e:
        print(f"   ✗ Invalid JSON: {e}")
        return False
    
    # 3. Verify database.bin
    print("\n3. Verifying database.bin...")
    bin_path = base / "database.bin"
    if not bin_path.exists():
        print("   ✗ database.bin not found!")
        return False
    
    with open(bin_path, "rb") as f:
        bin_data = f.read()
    
    # Check magic
    if bin_data[:4] != b"MTKB":
        print("   ✗ Invalid magic bytes!")
        return False
    print("   ✓ Magic bytes verified (MTKB)")
    
    # Parse header
    version = struct.unpack("<H", bin_data[4:6])[0]
    original_size = struct.unpack("<I", bin_data[6:10])[0]
    compressed_size = struct.unpack("<I", bin_data[10:14])[0]
    checksum = bin_data[14:30].hex()
    compressed_data = bin_data[30:]
    
    print(f"   ✓ Format version: {version}")
    print(f"   ✓ Original size: {original_size} bytes")
    print(f"   ✓ Compressed size: {compressed_size} bytes")
    
    # Verify checksum
    actual_checksum = hashlib.md5(compressed_data).hexdigest()
    if actual_checksum == checksum:
        print("   ✓ MD5 checksum verified")
    else:
        print("   ✗ MD5 checksum mismatch!")
        return False
    
    # Decompress and verify
    try:
        decompressed = zlib.decompress(compressed_data)
        if len(decompressed) == original_size:
            print(f"   ✓ Decompression successful ({len(decompressed)} bytes)")
        else:
            print(f"   ✗ Size mismatch after decompression!")
            return False
    except Exception as e:
        print(f"   ✗ Decompression failed: {e}")
        return False
    
    # 4. Verify resources
    print("\n4. Verifying resources...")
    all_ok = True
    for res in manifest.get("resources", []):
        res_path = base / "resources" / res["path"]
        if res_path.exists():
            with open(res_path, "rb") as f:
                actual_md5 = hashlib.md5(f.read()).hexdigest()
            if actual_md5 == res["md5"]:
                print(f"   ✓ {res['path']}")
            else:
                print(f"   ✗ {res['path']} - MD5 mismatch")
                all_ok = False
        else:
            print(f"   ⚠ {res['path']} - not found (optional)")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ PACKAGE VERIFICATION PASSED")
    else:
        print("✗ PACKAGE VERIFICATION FAILED")
    print("=" * 60)
    
    return all_ok

if __name__ == "__main__":
    verify_package()
