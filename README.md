# MusicToolkit Pro - Genre Database (CDN)

**Version**: v10.53 (Final Stable)
**Release Date**: 2026-09-19
**Total Genres**: 215
**Total WorkTypes**: 16
**Total Entries**: 231

---

## What's New in v10.53 (Final Stable)

### 🛡️ Stability & Safety
- All analysis modules wrapped in try-except for crash safety
- Boundary clipping: out-of-range segments clamped safely
- LUFS values clamped to [-90, 0] range, DR to [0, 40] dB
- Short segments (<2s) return safe defaults to avoid misdetection
- Zero crash tolerance: analysis never fails the whole app

### 🎛️ LoudnessAnalyzer (EBU R128 LUFS + DR)
- **Integrated LUFS** measurement per audio segment
- **Dynamic Range (DR)** = peak/RMS ratio in dB
- K-weighting filter (EBU R128 standard)
- 0.4s block / 0.1s hop window analysis
- LUFS genre reference thresholds for accuracy

### 🎤 VocalDetector (Vocal Presence Detection)
- 250~4000Hz vocal band energy analysis
- Auto-classifies: **Acapella** / **Instrumental** / **Normal vocal**
- Low-frequency energy ratio for distinction
- Confidence scoring (0-1 scale)
- Short segment safety: <2s returns neutral result

### 🆕 WorkType Library (16 total)
| WorkType | Chinese | Detection |
|----------|---------|-----------|
| Remix | 重混音 | `remix` |
| Bootleg | 非官方Remix | `bootleg` |
| Mashup | 混搭曲 | `mashup` + multi-BPM |
| Transition | 过渡段 | BPM linear ramp |
| Edit | 剪辑版 | `edit` |
| Extended Mix | 加长版 | `extended` |
| Original Mix | 原版 | `original mix` |
| VIP Mix | VIP混音版 | `vip mix` |
| Instrumental | 纯伴奏 | vocal detector |
| Acapella | 人声干声 | vocal detector |
| Dub Mix | Dub混音版 | `dub mix` |
| Radio Edit | 电台版 | `radio edit` |
| Rework | 重制改编 | `rework` |
| Re-Edit | 二次剪辑 | `re-edit` |
| Reconstruction Mix | 重构版 | `reconstruction` |
| Club Mix | 俱乐部版 | `club mix` |

### 🎯 Smart WorkType Logic
- **Acapella** → vocal_ratio > 0.65 + low_end < 15% → skips genre scoring
- **Instrumental** → no vocal + low_end > 35% → normal BPM genre scoring
- **Extended Mix / Radio Edit** → mutually exclusive
- **VIP Mix** vs **Remix** vs **Bootleg** → producer source distinction

### 📊 LUFS Reference by Genre
| Genre | LUFS | DR | Notes |
|-------|------|----|-------|
| Hardstyle / Bigroom | -7 ~ -10 | 3~6 | Heavy compression |
| Vina House / House | -8 ~ -11 | 5~8 | SE Asia club standard |
| Trance / Progressive | -9 ~ -13 | 6~9 | Melodic, lighter |
| Ballad | -12 ~ -16 | 10~16 | Wide dynamics |

---

## CDN URLs (jsDelivr - stable, global)

1. **manifest.json**
   ```
   https://cdn.jsdelivr.net/gh/MusicToolKitPro/Genres-Update@main/manifest.json
   ```

2. **data.json**
   ```
   https://cdn.jsdelivr.net/gh/MusicToolKitPro/Genres-Update@main/data.json
   ```

---

## Security

- SHA256 checksums verified on every update
- Firewall restricts to trusted CDN domains only
- Auto-update runs in background on startup
- Backup required before applying updates

## Verification

```bash
python verify_package.py
```

---

## Version History

### v10.53 (2026-09-19) - Final Stable
- LoudnessAnalyzer + VocalDetector stabilized
- Boundary protection and exception handling
- 16 total WorkTypes
- Zero-crash analysis pipeline

### v10.52 (2026-09-19)
- Initial LUFS + DR analysis
- Vocal detection module
- 9 new DJ WorkType versions

### v10.51 (2026-09-19)
- Audio segment analysis engine
- WorkType classification
- Fingerprint matching (AcoustID/Chromaprint)

### v10.50 (2026-09-18)
- Initial CDN release with 215 genres
- jsDelivr auto-update support
- SHA256 verification

---
*MusicToolkit Pro Release System*
