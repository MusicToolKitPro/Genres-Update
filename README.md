# MusicToolkit Pro - Genre Database Upload Package

## Package Information
- **Version**: 1.47.0
- **Generated**: 2026-09-18 10:28:30
- **Total Genres**: 215
- **Bar Common Genres**: 203

## Package Contents

```
upload_package/
├── manifest.json          # Package manifest with checksums
├── data.json              # Genre database (JSON format, human-readable)
├── database.bin           # Genre database (compressed binary format)
├── README.md              # This file
└── resources/             # Additional resource files
    ├── assets/            # Images and media assets
    └── scripts/           # Core analysis scripts
```

## File Descriptions

### 1. manifest.json
Package manifest containing:
- Package version and metadata
- Database file checksums (MD5 + SHA256)
- Resource file inventory with checksums
- Update instructions and compatibility info
- Security configuration

### 2. data.json
Full genre database in JSON format:
- 215 genre entries
- Each entry contains: BPM range, beat type, kick feature, timbre, rhythm, vocal properties
- Spectrum profile (6 frequency bands)
- Transient profile
- Distortion profile
- Dynamic profile (LUFS, peak/RMS ratio)
- Tags and aliases for multi-language support

### 3. database.bin
Compressed binary version of the database:
- Format: MTKB magic + version + sizes + MD5 checksum + zlib compressed data
- Compression ratio: ~6.3x smaller than JSON
- For fast loading in production environments

## Upload Instructions

### Option 1: GitHub Gist (Recommended)
1. Create a new GitHub Gist
2. Upload `data.json` as a file named `genres.json`
3. Copy the raw URL (should end with `/raw/`)
4. In MusicToolkit Pro: Settings → Network Update → Set Update URL
5. Click "Check for Updates Now"

### Option 2: GitHub Repository
1. Create a new GitHub repository
2. Upload `data.json` to the repository
3. Get the raw file URL
4. Configure in MusicToolkit Pro settings

### Option 3: CDN (jsDelivr)
1. Upload to any GitHub repository
2. Use jsDelivr CDN URL: `https://cdn.jsdelivr.net/gh/USER/REPO/genres.json`
3. Configure in MusicToolkit Pro settings

### Option 4: Local Manual Update
1. Copy `data.json` content
2. Replace `scripts/genres.json` in the application directory
3. Restart the application

## Security Notes

- All files include MD5 and SHA256 checksums in manifest.json
- The application verifies checksums before applying updates
- Only whitelisted domains are allowed for updates:
  - raw.githubusercontent.com
  - gist.githubusercontent.com
  - cdn.jsdelivr.net
  - api.github.com

## Genre Categories

- **house**: 35 genres
- **urban**: 26 genres
- **techno**: 16 genres
- **hardcore_rave**: 14 genres
- **trance**: 12 genres
- **ambient_chill**: 12 genres
- **internet_modern**: 11 genres
- **retro_electro_80s**: 10 genres
- **bounce**: 9 genres
- **global_club**: 9 genres
- **bass_music**: 8 genres
- **drum_and_bass**: 8 genres
- **breakbeat**: 5 genres
- **retro**: 5 genres
- **other**: 5 genres

## Verification

To verify package integrity:
```bash
# Check MD5
md5sum data.json database.bin

# Compare with manifest.json values
```

## Changelog

### v1.47.0
- Added professional BPM detector (5 strategies + comb filter + grid alignment)
- Added network update module with security firewall
- Added 215 genres with full spectrum/transient/distortion/dynamic profiles
- Optimized Party Break vs Vina House classification
- Added filename genre reference engine
- Added smart deduplication system
