# MusicToolkit Pro - Genre Database Update

## Version: v12.0.01 (2026-09-20)

### Overview
MusicToolkit Pro is a professional DJ audio analysis toolkit for Windows.
This repository contains the genre database that the software automatically downloads via CDN.

### Genre Database (2010-2026)
- **22 core DJ genres** covering 2010 EDM wave to 2026 current charts
- **16 WorkTypes** (Remix / Mashup / Transition / Bootleg / Edit / VIP Mix / Instrumental / Acapella / Dub Mix / Radio Edit / Extended Mix / Rework / Re-Edit / Reconstruction Mix / Club Mix)
- **14 DJ platforms** for track lookup and promotion

### Supported Genres
Bigroom House, Progressive House, Electro House, Melbourne Bounce, Chinese Bounce,
Vina House, Hardstyle, Hard Bounce, Trance, Psytrance, Future Bass, EDM Trap,
Dubstep, Tech House, Melodic Techno, Afro House, Amapiano, Drum and Bass,
Hip Hop, Phonk, Thai Breakbeat, Deep House

### Key Features
1. **Filename Priority Detection** - Genre keywords in filenames take highest priority
2. **Sliding Window Segment Analysis** - Detects Mashup / multi-genre transitions
3. **Mutual Exclusion Scoring** - Prevents Vina House vs Chinese Bounce confusion
4. **BPM Auto-Halving** - DJ standard (Rekordbox/Serato convention)
5. **LUFS Loudness + Dynamic Range** - EBU R128 standard
6. **Vocal Detection** - Distinguishes Acapella / Instrumental
7. **Drop Detection** - Identifies build-up → drop transitions
8. **Timbre Tagging** - BassHeavy / Dark / Bright / Balanced
9. **Hardware Binding** - Anti-copy protection
10. **Feedback System** - User corrections emailed to developer for DB improvement

### CDN Auto-Update
- Manifest: https://cdn.jsdelivr.net/gh/MusicToolKitPro/Genres-Update@main/manifest.json
- Data: https://cdn.jsdelivr.net/gh/MusicToolKitPro/Genres-Update@main/data.json

### Software Requirements
- Windows 10/11
- No Python required (standalone exe)
- Auto-installs all dependencies

### Release Notes
**v12.0.01 (2026-09-20)**
- New 22-genre 2010-2026 database with quantitative audio features
- Sliding window segment analysis for Mashup detection
- Mutual exclusion scoring to reduce genre confusion
- Filename-first genre detection (DJ file naming convention)
- Hardware fingerprint binding (anti-copy)
- Genre feedback collection (auto-email on app close)
- M3U playlist export
- DJ platform search (Beatport / SoundCloud / Traxsource)
- 30000+ file treeview support
- Full Chinese/English UI switch