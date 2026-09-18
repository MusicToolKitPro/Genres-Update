"""
Verify MusicToolkit Pro genre database package integrity.
Usage: python verify_package.py
"""
import json
import hashlib
import struct
import zlib
from pathlib import Path

def verify_package():
    base = Path(__file__).parent
    print("=" * 60)
    print("MusicToolkit Pro - Package Verification")
    print("=" * 60)
    
    print("\n1. Loading manifest.json...")
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        print("   ✗ manifest.json not found!")
        return False
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    print(f"   ✓ Version: {manifest.get('version')}")
    print(f"   ✓ Genres: {manifest.get('total_genres')}")
    
    print("\n2. Verifying data.json SHA256...")
    data_path = base / "data.json"
    if not data_path.exists():
        print("   ✗ data.json not found!")
        return False
    
    with open(data_path, "rb") as f:
        data_bytes = f.read()
    actual_sha256 = hashlib.sha256(data_bytes).hexdigest()
    expected_sha256 = manifest.get("checksums", {}).get("data_json_sha256", "")
    
    if actual_sha256.lower() == expected_sha256.lower():
        print(f"   ✓ SHA256 VERIFIED")
    else:
        print(f"   ✗ SHA256 MISMATCH!")
        print(f"     Expected: {expected_sha256}")
        print(f"     Actual:   {actual_sha256}")
        return False
    
    print("\n3. Verifying data.json content...")
    try:
        genres = json.loads(data_bytes)
        if isinstance(genres, list):
            print(f"   ✓ Valid JSON array with {len(genres)} genres")
        else:
            print(f"   ✗ Expected JSON array")
            return False
    except Exception as e:
        print(f"   ✗ Invalid JSON: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ PACKAGE VERIFICATION PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    verify_package()
