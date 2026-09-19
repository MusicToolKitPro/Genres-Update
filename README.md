# MusicToolkit Pro Genre Database

**Version:** v10.54
**Release Date:** 2026-09-19
**Total Entries:** 230 (214 Genres + 16 WorkTypes)

---

## 📦 What's New in v10.54

### 🆕 New Analysis Modules
- **DropDetector**: Detects Build-up → Drop explosion points using RMS + low-frequency energy gradient
  - Outputs: has_drop, drop_confidence, drop_relative_time
  - Drop confidence > 0.6 = high confidence, 0.45-0.6 = suspected
  - Shows as 💥Drop in the status column

- **TimbreTagger**: Classifies timbre characteristics
  - **BassHeavy**: Low-frequency ratio > 42% (Hardstyle, Bounce, Vina House)
  - **Dark**: Spectral centroid < 1600Hz (Deep House, Dark Techno)
  - **Bright**: Spectral centroid > 3200Hz (Trance, Melodic Pop)
  - **Balanced**: Equal low/high frequency (General pop, House)

### 🔧 CRITICAL FIX: Genre Bias Removal
**Previous problem**: All unclear audio was defaulting to Vina House due to scoring bias.

**Root causes fixed:**
1. ✅ **Removed confidence_weight × 2 multiplier** - Previously amplified high-weight genres
2. ✅ **Normalized all 214 genres to equal weight (0.85)** - No genre gets built-in advantage
3. ✅ **Removed duplicate vina_bounce entry** - Eliminated double-voting for Vina House
4. ✅ **Narrowed Vina House BPM range** - From 126-145 to **132-142** (more specific, matches real Vina House)
5. ✅ **Reduced confidence_weight impact in scoring** - Multiplied by 0.5 instead of flat bonus

**Result**: Genre classification is now purely based on audio feature matching (BPM, spectrum, dynamics, vocals). No genre has a "default win" advantage.

### 📊 Analysis Pipeline (Complete)
```
Audio File
├─ BPM Detection (multi-resolution)
├─ Key Detection (Camelot wheel)
├─ Genre Scoring (214 genres, equal weight)
├─ WorkType Detection (16 types: Remix/Mashup/Acapella/etc.)
├─ LUFS Loudness (EBU R128)
├─ Dynamic Range (DR)
├─ Vocal Detection (has_vocal + confidence)
├─ Drop Detection 🆕 (has_drop + confidence + timestamp)
└─ Timbre Tagging 🆕 (BassHeavy/Dark/Bright/Balanced)
```

---

## 📁 Repository Structure

```
Genres-Update/
├── manifest.json      # Version info, checksums, changelog
├── data.json          # Full genre database (230 entries)
├── genres.json        # Same as data.json (backup copy)
├── README.md          # This file
└── verify_package.py  # Verification script
```

---

## 🔄 Auto-Update

The software automatically checks for updates on startup via jsDelivr CDN:
- Manifest: `https://cdn.jsdelivr.net/gh/MusicToolKitPro/Genres-Update@main/manifest.json`
- Data: `https://cdn.jsdelivr.net/gh/MusicToolKitPro/Genres-Update@main/data.json`

**No user action required** - updates are downloaded and applied automatically.

---

## 🔒 Security

- All files verified with SHA256 checksum
- CDN multi-source fallback: jsDelivr → GitHub Raw → Fastly
- Only official sources allowed (cdn.jsdelivr.net, raw.githubusercontent.com)

---

## 📝 Version History

| Version | Date | Changes |
|---------|------|---------|
| v10.54 | 2026-09-19 | DropDetector + TimbreTagger + Genre bias fix |
| v10.53 | 2026-09-19 | LUFS + Vocal detection + 9 new WorkTypes |
| v10.52 | 2026-09-19 | AudioSegmentAnalyzer + Mashup detection |
| v10.51 | 2026-09-18 | Initial 231-entry genre database |
