#!/usr/bin/env python3
"""Music analysis: BPM, Key, Genre classification with detailed genre profiles."""
import numpy as np
import librosa
import json
try:
    from genre_score_engine import genre_score_engine, convert_features_to_engine_format
    ENGINE_AVAILABLE = True
except:
    ENGINE_AVAILABLE = False
import sys
import os
from pathlib import Path


def _load_genres():
    """Load genres from genres.json, fallback to embedded list."""
    script_dir = Path(__file__).parent
    json_path = script_dir / "genres.json"
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    if hasattr(sys, '_MEIPASS'):
        meipass_path = Path(sys._MEIPASS) / "scripts" / "genres.json"
        if meipass_path.exists():
            try:
                with open(meipass_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return []


GENRES = _load_genres()

# Pre-compute genre scoring targets for speed
def _parse_vocal_prop(val):
    """Parse vocal_prop which can be a float or a Chinese description string."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.lower()
        if "无" in val or "none" in s or "no vocal" in s:
            return 0.0
        if "极高" in val or "very high" in s:
            return 0.95
        if "高" in val and "中" not in val and "低" not in val:
            return 0.85
        if "中高" in val or "medium-high" in s or "mid-high" in s:
            return 0.70
        if "中" in val and "高" not in val and "低" not in val:
            return 0.50
        if "中低" in val or "medium-low" in s or "mid-low" in s:
            return 0.30
        if "低" in val and "中" not in val:
            return 0.15
        if "极低" in val or "very low" in s:
            return 0.05
    return 0.3




# ==============================================
# Feature Cache Mechanism
# ==============================================
import hashlib
_appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
CACHE_DIR = _appdata / "MusicToolkit" / "SData" / "feature_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_key(audio_path):
    """Generate cache key from file path + modification time + size."""
    try:
        stat = os.stat(audio_path)
        key_str = f"{audio_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key_str.encode()).hexdigest()
    except:
        return hashlib.md5(audio_path.encode()).hexdigest()

def _load_features_from_cache(cache_key):
    """Load extracted features from cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def _save_features_to_cache(cache_key, features):
    """Save extracted features to cache."""
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(features, f)
    except:
        pass



# ==============================================
_GENRE_TARGETS = []
for g in GENRES:
    is_detailed = g.get("data_quality") == "detailed"
    target = {
        "is_detailed": is_detailed,
        "style_en": g.get("style_en", ""),
        "parent_category": g.get("parent_category", "other"),
        "bpm_min": g["bpm_min"],
        "bpm_max": g["bpm_max"],
        "bpm_mid": (g["bpm_min"] + g["bpm_max"]) / 2,
        "bpm_range": (g["bpm_max"] - g["bpm_min"]) / 2,
        "bpm_weight": 25 if is_detailed else 35,  # Reduced BPM weight
        "vocal_prop": _parse_vocal_prop(g.get("vocal_prop", 0.3)),
        "vocal_weight": 8 if is_detailed else 12,
        "confidence_weight": 2 * g.get("confidence_weight", 0.9),
        "tags": [t.lower() for t in g.get("tags", [])],
    }
    if is_detailed and g.get("spectrum_profile"):
        sp = g["spectrum_profile"]
        # Full 6-band spectrum profile for precise matching
        target["spectrum_full"] = [
            sp.get("sub_energy", 0),
            sp.get("lf_energy", 0),
            sp.get("lmf_energy", 0),
            sp.get("mf_energy", 0),
            sp.get("hmf_energy", 0),
            sp.get("hf_energy", 0),
        ]
        target["lf_target"] = sp.get("sub_energy", 0) + sp.get("lf_energy", 0)
        target["hf_target"] = sp.get("hmf_energy", 0) + sp.get("hf_energy", 0)
        target["mid_target"] = sp.get("lmf_energy", 0) + sp.get("mf_energy", 0)
    if is_detailed and g.get("transient_profile"):
        tp = g["transient_profile"]
        target["global_transient"] = tp.get("global_transient", 0.7)
        target["kick_transient"] = tp.get("kick_transient", 0.8)
        target["kick_transient_ms"] = tp.get("kick_transient_time_ms", 10)
    if is_detailed and g.get("distortion_profile"):
        dp = g["distortion_profile"]
        target["dist_target"] = max(0, min(1, 1 - dp.get("distortion_snr_db", 15) / 25))
        target["dist_snr"] = dp.get("distortion_snr_db", 15)
    if is_detailed and g.get("dynamic_profile"):
        dynp = g["dynamic_profile"]
        target["loud_target"] = max(0, min(1, (dynp.get("loudness_target_lufs", -8) + 15) / 12))
        target["peak_rms_ratio"] = dynp.get("peak_rms_ratio", 2.0)
    _GENRE_TARGETS.append(target)

CATS = {
    "house": ("House", "浩室"), "bounce": ("Bounce", "弹跳"),
    "techno": ("Techno", "科技"), "trance": ("Trance", "出神"),
    "hard_dance": ("Hard Dance", "硬派舞曲"), "hardcore_rave": ("Hardcore Rave", "硬核锐舞"),
    "urban": ("Urban", "都市"), "dnb": ("D&B", "鼓打贝斯"),
    "ambient": ("Ambient", "氛围"), "retro": ("Retro", "复古"),
    "other": ("Other", "其他"), "bass_music": ("Bass Music", "贝斯音乐"),
    "drum_and_bass": ("Drum & Bass", "鼓打贝斯"), "breakbeat": ("Breakbeat", "碎拍"),
    "ambient_chill": ("Ambient Chill", "氛围弛放"), "retro_electro_80s": ("Retro Electro", "复古电子"),
    "global_club": ("Global Club", "全球俱乐部"), "industrial_ebm": ("Industrial EBM", "工业EBM"),
    "internet_modern": ("Internet Modern", "互联网现代"), "cn_edm": ("CN EDM", "中文电子"),
    "hardstyle": ("Hardstyle", "硬派")
}


def _safe_float(arr):
    """Safely convert numpy array or scalar to float."""
    val = np.asarray(arr)
    if val.ndim == 0:
        return float(val)
    return float(np.mean(val))


def _detect_bpm_enhanced(y, sr):
    """Professional DJ-grade BPM detection with multi-strategy voting.
    
    Uses 7 detection strategies:
    1. librosa beat_track (default)
    2. beat_track with tightness=100 (electronic 4/4 optimized)
    3. beat_track with hop_length=256 (fast response)
    4. Onset strength autocorrelation
    5. Tempogram analysis
    6. Spectral flux onset detection + autocorrelation
    7. Beat tracking with start_bpm estimation
    
    Then uses weighted clustering to select the most reliable BPM.
    """
    import numpy as np
    candidates = []
    weights = []  # Weight for each candidate based on detector reliability

    # Strategy 1: librosa beat_track with default params (weight: 1.0)
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm1 = _safe_float(tempo)
        if 50 < bpm1 < 250:
            candidates.append(bpm1)
            weights.append(1.0)
    except: pass

    # Strategy 2: beat_track with tighter tracking (better for electronic 4/4) (weight: 1.3)
    try:
        tempo2, _ = librosa.beat.beat_track(y=y, sr=sr, tightness=100, start_bpm=128)
        bpm2 = _safe_float(tempo2)
        if 50 < bpm2 < 250:
            candidates.append(bpm2)
            weights.append(1.3)
    except: pass

    # Strategy 3: beat_track with hop_length=256 (faster response) (weight: 0.9)
    try:
        tempo3, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=256, start_bpm=128)
        bpm3 = _safe_float(tempo3)
        if 50 < bpm3 < 250:
            candidates.append(bpm3)
            weights.append(0.9)
    except: pass

    # Strategy 4: Onset strength autocorrelation (weight: 1.1)
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        ac = np.correlate(onset_env, onset_env, mode='full')
        ac = ac[len(ac)//2:]
        min_lag = int(60 * sr / (512 * 200))
        max_lag = int(60 * sr / (512 * 60))
        if min_lag < len(ac) and max_lag < len(ac) and max_lag > min_lag:
            peak_region = ac[min_lag:max_lag]
            if len(peak_region) > 0:
                peak_lag = np.argmax(peak_region) + min_lag
                if peak_lag > 0:
                    bpm4 = 60.0 * sr / (512 * peak_lag)
                    if 50 < bpm4 < 250:
                        candidates.append(bpm4)
                        weights.append(1.1)
    except: pass

    # Strategy 5: Tempogram analysis (weight: 1.2)
    try:
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tg_bpm = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
        bpm5 = _safe_float(tg_bpm)
        if 50 < bpm5 < 250:
            candidates.append(bpm5)
            weights.append(1.2)
    except: pass

    # Strategy 6: Spectral flux onset detection (weight: 1.0)
    try:
        S = np.abs(librosa.stft(y, n_fft=1024, hop_length=512))
        spectral_flux = np.mean(np.diff(S, axis=1), axis=0)
        spectral_flux = np.maximum(0, spectral_flux)
        ac_sf = np.correlate(spectral_flux, spectral_flux, mode='full')
        ac_sf = ac_sf[len(ac_sf)//2:]
        min_lag_sf = int(60 * sr / (512 * 200))
        max_lag_sf = int(60 * sr / (512 * 60))
        if min_lag_sf < len(ac_sf) and max_lag_sf < len(ac_sf) and max_lag_sf > min_lag_sf:
            peak_region_sf = ac_sf[min_lag_sf:max_lag_sf]
            if len(peak_region_sf) > 0:
                peak_lag_sf = np.argmax(peak_region_sf) + min_lag_sf
                if peak_lag_sf > 0:
                    bpm6 = 60.0 * sr / (512 * peak_lag_sf)
                    if 50 < bpm6 < 250:
                        candidates.append(bpm6)
                        weights.append(1.0)
    except: pass

    # Strategy 7: Beat tracking with adaptive start_bpm (weight: 0.8)
    try:
        # Estimate start_bpm from onset envelope
        onset_env7 = librosa.onset.onset_strength(y=y, sr=sr)
        tempo_est = librosa.feature.tempo(onset_envelope=onset_env7, sr=sr)
        start_bpm = _safe_float(tempo_est)
        if not (60 < start_bpm < 200):
            start_bpm = 128
        tempo7, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=start_bpm, tightness=50)
        bpm7 = _safe_float(tempo7)
        if 50 < bpm7 < 250:
            candidates.append(bpm7)
            weights.append(0.8)
    except: pass

    if not candidates:
        return 120.0

    # Weighted clustering: cluster candidates within 3% tolerance
    from collections import defaultdict
    clusters = defaultdict(lambda: {'bpms': [], 'weights': []})
    
    for bpm, w in zip(candidates, weights):
        placed = False
        for center in list(clusters.keys()):
            if abs(bpm - center) < center * 0.03:
                clusters[center]['bpms'].append(bpm)
                clusters[center]['weights'].append(w)
                placed = True
                break
        if not placed:
            clusters[bpm]['bpms'].append(bpm)
            clusters[bpm]['weights'].append(w)

    # Find the cluster with highest total weight
    best_center = max(clusters.keys(), key=lambda c: sum(clusters[c]['weights']))
    best_cluster = clusters[best_center]
    
    # Calculate weighted average of best cluster
    total_weight = sum(best_cluster['weights'])
    if total_weight > 0:
        cluster_bpm = sum(b * w for b, w in zip(best_cluster['bpms'], best_cluster['weights'])) / total_weight
    else:
        cluster_bpm = float(np.mean(best_cluster['bpms']))

    # Octave correction: check if half or double is more likely
    median_bpm = cluster_bpm

    # For electronic music, prefer BPM in 120-150 range
    # If median is very low (<85), check if double makes more sense
    if median_bpm < 85:
        double_bpm = median_bpm * 2
        near_double = sum(w for b, w in zip(candidates, weights) if abs(b - double_bpm) < double_bpm * 0.05)
        near_original = sum(w for b, w in zip(candidates, weights) if abs(b - median_bpm) < median_bpm * 0.05)
        if near_double > near_original:
            median_bpm = double_bpm

    # If median is very high (>175), check if half makes more sense
    elif median_bpm > 175:
        half_bpm = median_bpm / 2
        near_half = sum(w for b, w in zip(candidates, weights) if abs(b - half_bpm) < half_bpm * 0.05)
        near_original = sum(w for b, w in zip(candidates, weights) if abs(b - median_bpm) < median_bpm * 0.05)
        if near_half > near_original:
            median_bpm = half_bpm

    # For DJ use: round to nearest integer if close
    if abs(median_bpm - round(median_bpm)) < 0.2:
        return float(round(median_bpm))
    return round(median_bpm, 1)


def check_audio_quality(filepath, duration=30):
    """Analyze audio quality and determine if enhancement is needed.

    Returns dict with:
        quality_score: 0-100 (higher is better)
        needs_enhancement: bool
        issues: list of detected issues
        recommendations: dict of recommended enhancement settings
    """
    try:
        y, sr = librosa.load(filepath, sr=None, mono=True, duration=duration)
        if len(y) < sr:
            return {"quality_score": 50, "needs_enhancement": False, "issues": ["Too short to analyze"], "recommendations": {}}

        issues = []
        score = 100

        # 1. RMS loudness check
        rms = float(np.sqrt(np.mean(y**2)))
        rms_db = 20 * np.log10(rms + 1e-10)
        if rms_db < -25:
            issues.append(f"Low volume ({rms_db:.1f} dB)")
            score -= 20
        elif rms_db > -8:
            issues.append(f"Very loud ({rms_db:.1f} dB), possible clipping")
            score -= 10

        # 2. Peak / clipping check
        peak = float(np.max(np.abs(y)))
        if peak > 0.98:
            issues.append("Possible clipping (peak near 0 dBFS)")
            score -= 15

        # 3. Dynamic range
        peak_rms_ratio = peak / (rms + 1e-10)
        if peak_rms_ratio < 4:
            issues.append("Compressed dynamic range")
            score -= 10
        elif peak_rms_ratio > 20:
            issues.append("Very wide dynamic range, may need normalization")
            score -= 5

        # 4. Spectral analysis
        S = np.abs(librosa.stft(y, n_fft=2048))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
        total_energy = np.sum(S**2) + 1e-10

        # High frequency energy (above 8kHz) - hiss detection
        hf_mask = freqs > 8000
        hf_energy = np.sum(S[hf_mask]**2) / total_energy
        if hf_energy > 0.15:
            issues.append("Excessive high frequency content (possible hiss)")
            score -= 10

        # Low frequency energy (below 100Hz) - muddiness
        lf_mask = freqs < 100
        lf_energy = np.sum(S[lf_mask]**2) / total_energy
        if lf_energy > 0.4:
            issues.append("Excessive low frequency (muddy bass)")
            score -= 10

        # Mid frequency energy (100Hz-8kHz)
        mf_mask = (freqs >= 100) & (freqs <= 8000)
        mf_energy = np.sum(S[mf_mask]**2) / total_energy
        if mf_energy < 0.5:
            issues.append("Weak midrange")
            score -= 5

        # 5. Noise floor estimation (spectral flatness)
        spectral_flatness = float(np.mean(librosa.feature.spectral_flatness(y=y, S=S)))
        if spectral_flatness > 0.5:
            issues.append("High noise floor (noisy recording)")
            score -= 15

        # 6. Zero crossing rate (noisiness)
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        if zcr > 0.15:
            issues.append("High zero crossing rate (noisy/bright)")
            score -= 5

        score = max(0, min(100, score))
        needs_enhancement = score < 70 or len(issues) >= 2

        # Build recommendations
        recommendations = {}
        if rms_db < -20 or peak_rms_ratio > 15:
            recommendations["normalize"] = True
            recommendations["target"] = -14.0
        if peak > 0.95:
            recommendations["peak_normalize"] = True
        if spectral_flatness > 0.4 or hf_energy > 0.12:
            recommendations["denoise"] = True
            recommendations["denoise_strength"] = 0.7
        if lf_energy > 0.35:
            recommendations["bass"] = -1.5
        if hf_energy > 0.12 and spectral_flatness < 0.4:
            recommendations["treble"] = -1.0
        if mf_energy < 0.55:
            recommendations["clarity"] = 1.5

        return {
            "quality_score": round(score, 1),
            "needs_enhancement": needs_enhancement,
            "issues": issues,
            "recommendations": recommendations,
            "rms_db": round(rms_db, 1),
            "peak": round(peak, 3),
            "spectral_flatness": round(spectral_flatness, 3),
        }
    except Exception as e:
        return {"quality_score": 50, "needs_enhancement": False, "issues": [f"Analysis error: {str(e)}"], "recommendations": {}}


def analyze_audio(filepath, duration=30):
    """Analyze audio file: BPM, Key, Genre classification with multi-segment analysis.

    Args:
        filepath: Path to audio file
        duration: Analysis duration in seconds (default 30 for speed)
    """
    # Check feature cache first
    cache_key = _get_cache_key(filepath)
    cached = _load_features_from_cache(cache_key)
    if cached and cached.get("duration_sec", 0) > 0:
        # Return cached result (features don't change for same file)
        cached["from_cache"] = True
        return cached
    
    # Check feature cache first
    
    try:
        y, sr = librosa.load(filepath, duration=duration, mono=True)
    except Exception as e:
        return {"error": str(e), "file": filepath, "filename": Path(filepath).name,
                "song_info": {"title": Path(filepath).stem, "artist": ""},
                "bpm": 0, "key": "-", "genre": "Error", "genre_cn": "错误",
                "duration_sec": 0, "confidence": 0}

    # Get full file duration (not just analysis segment)
    try:
        full_duration = float(librosa.get_duration(filename=filepath))
    except Exception:
        try:
            import soundfile as sf
            info = sf.info(filepath)
            full_duration = float(info.duration)
        except Exception:
            full_duration = len(y) / sr

    if len(y) < sr * 2:
        return {"error": "Audio too short", "file": filepath, "filename": Path(filepath).name,
                "song_info": {"title": Path(filepath).stem, "artist": ""},
                "bpm": 0, "key": "-", "genre": "Error", "genre_cn": "错误",
                "duration_sec": round(len(y) / sr, 2), "confidence": 0}

    # Multi-segment analysis: 3 segments for stability
    seg_len = min(len(y), int(sr * 10))
    segments = []
    if len(y) > seg_len * 2:
        # Start, middle, end segments
        segments.append(y[:seg_len])
        segments.append(y[len(y)//2 - seg_len//2 : len(y)//2 + seg_len//2])
        segments.append(y[-seg_len:])
    else:
        segments.append(y)

    # Aggregate features across segments
    bpm_list = []
    sc_list, ro_list, zcr_list, onset_list, rms_list = [], [], [], [], []
    contrast_list, bw_list = [], []
    mfcc_means = []
    chroma_all = []
    subband_energies = []

    for seg in segments:
        if len(seg) < sr: continue
        # BPM per segment - enhanced multi-strategy detection
        try:
            bpm_seg = _detect_bpm_enhanced(seg, sr)
            bpm_list.append(bpm_seg)
        except: pass
        # Spectral features
        try:
            sc_list.append(_safe_float(np.mean(librosa.feature.spectral_centroid(y=seg, sr=sr))))
            ro_list.append(_safe_float(np.mean(librosa.feature.spectral_rolloff(y=seg, sr=sr))))
            zcr_list.append(_safe_float(np.mean(librosa.feature.zero_crossing_rate(seg))))
            oe = librosa.onset.onset_strength(y=seg, sr=sr)
            onset_list.append(_safe_float(np.mean(oe)))
            rms_list.append(_safe_float(np.mean(librosa.feature.rms(y=seg))))
            contrast_list.append(_safe_float(np.mean(librosa.feature.spectral_contrast(y=seg, sr=sr))))
            bw_list.append(_safe_float(np.mean(librosa.feature.spectral_bandwidth(y=seg, sr=sr))))
        except: pass
        # MFCC
        try:
            mfcc = librosa.feature.mfcc(y=seg, sr=sr, n_mfcc=13)
            mfcc_means.append(np.mean(mfcc, axis=1))
        except: pass
        # Chroma
        try:
            chroma = librosa.feature.chroma_cqt(y=seg, sr=sr)
            chroma_all.append(np.mean(chroma, axis=1))
        except: pass
        # Subband energy ratios (6 bands)
        try:
            S = np.abs(librosa.stft(seg, n_fft=2048))
            freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
            band_edges = [0, 60, 250, 1000, 3000, 8000, sr/2]  # Aligned with PANNs 6-band division
            band_e = []
            total_e = np.sum(S**2) + 1e-10
            for bi in range(len(band_edges)-1):
                mask = (freqs >= band_edges[bi]) & (freqs < band_edges[bi+1])
                band_e.append(float(np.sum(S[mask]**2) / total_e))
            subband_energies.append(band_e)
        except: pass

    # Aggregate
    bpm = round(float(np.median(bpm_list)) if bpm_list else 120.0, 1)
    sc = float(np.mean(sc_list)) if sc_list else 2500
    ro = float(np.mean(ro_list)) if ro_list else 6000
    zcr = float(np.mean(zcr_list)) if zcr_list else 0.05
    onset = float(np.mean(onset_list)) if onset_list else 0.5
    rms = float(np.mean(rms_list)) if rms_list else 0.1
    contrast = float(np.mean(contrast_list)) if contrast_list else 25
    bw = float(np.mean(bw_list)) if bw_list else 2500

    # Key detection from aggregated chroma
    try:
        cm = np.mean(chroma_all, axis=0) if chroma_all else np.zeros(12)
        ki = int(np.argmax(cm))
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        major_prof = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=float)
        minor_prof = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0], dtype=float)
        rolled = np.roll(cm, -ki)
        mode = "major" if np.corrcoef(rolled, major_prof)[0, 1] > np.corrcoef(rolled, minor_prof)[0, 1] else "minor"
        key = f"{notes[ki]} {mode}"
    except Exception:
        key = "-"

    # Subband energy (averaged)
    if subband_energies:
        sb = np.mean(subband_energies, axis=0)
        sub_energy = float(sb[0])  # 0-60Hz
        lf_energy = float(sb[1])   # 60-250Hz
        lmf_energy = float(sb[2])  # 250-2000Hz
        hmf_energy = float(sb[3])  # 2000-6000Hz
        hf_energy = float(sb[4] + sb[5])  # 6000+
    else:
        sub_energy = max(0, min(1, 1 - (sc - 1500) / 4000)) * 0.3
        lf_energy = max(0, min(1, 1 - (sc - 1500) / 4000)) * 0.4
        lmf_energy = 0.2
        hmf_energy = max(0, min(1, (sc - 1500) / 4000)) * 0.3
        hf_energy = max(0, min(1, (sc - 1500) / 4000)) * 0.2

    # Derived estimates
    vocal = min(1., max(0., 0.4 + (sc - 1800) / 3500 + hmf_energy * 0.3))
    distortion_est = max(0, min(1, (zcr - 0.025) / 0.10))
    transient_est = max(0, min(1, (onset - 0.25) / 1.0))
    loudness_est = max(0, min(1, rms / 0.22))
    lf_total = sub_energy + lf_energy
    hf_total = hmf_energy + hf_energy

    if not GENRES or not _GENRE_TARGETS:
        return {"error": "No genres loaded", "file": filepath, "filename": Path(filepath).name,
                "song_info": {"title": Path(filepath).stem, "artist": ""},
                "bpm": bpm, "key": key, "genre": "Unknown", "genre_cn": "未知",
                "duration_sec": round(full_duration, 2), "confidence": 0}

    # Hierarchical pre-classification: determine if this is dance music or non-dance
    is_dance_music = (
        bpm >= 110 and 
        onset >= 0.4 and 
        rms >= 0.06 and 
        lf_total >= 0.35
    )
    is_slow_ballad = (
        bpm <= 90 and 
        rms <= 0.10 and 
        vocal >= 0.5
    )
    
    # Compute full 6-band spectrum vector for matching
    spectrum_vec = [sub_energy, lf_energy, lmf_energy, 0.0, hmf_energy, hf_energy]
    # Fill mf_energy from remaining mid band
    spectrum_vec[3] = max(0, 1.0 - sum(spectrum_vec) + spectrum_vec[3])
    
    # Compute MFCC-based timbre similarity (if available)
    mfcc_ref = np.mean(mfcc_means, axis=0) if mfcc_means else np.zeros(13)
    
    # Genre classification with enhanced multi-feature scoring
    best_score = -1
    best_idx = 0
    scores = []
    for i, t in enumerate(_GENRE_TARGETS):
        score = 0.0
        
        # Hierarchical filtering: penalize mismatched categories
        cat = t.get("parent_category", "other")
        dance_cats = {"house", "techno", "trance", "hard_dance", "hardcore_rave", 
                       "dnb", "drum_and_bass", "bass_music", "breakbeat", "bounce",
                       "global_club", "industrial_ebm", "cn_edm", "african_club",
                       "latin_club", "uk_garage", "trap", "pop_electronic"}
        non_dance_cats = {"pop", "rock", "rnb_soul", "folk", "ambient_chill", "ambient"}
        
        if is_dance_music and cat in non_dance_cats:
            score -= 15  # Heavy penalty for dance track matching non-dance genre
        if is_slow_ballad and cat in dance_cats:
            score -= 15  # Heavy penalty for ballad matching dance genre

        # BPM score - tighter Gaussian with hard range penalty
        bpm_diff = abs(bpm - t["bpm_mid"])
        if t["bpm_min"] <= bpm <= t["bpm_max"]:
            score += t["bpm_weight"]
        else:
            # Outside range: steep penalty
            bpm_penalty = np.exp(-(bpm_diff**2) / (2 * (t["bpm_range"])**2))
            score += t["bpm_weight"] * bpm_penalty * 0.5  # Halved outside range

        # Detailed features - enhanced weighting
        if t["is_detailed"]:
            # Full 6-band spectrum matching (most important for detailed genres)
            if "spectrum_full" in t:
                spec_diff = sum(abs(spectrum_vec[j] - t["spectrum_full"][j]) for j in range(6))
                spec_score = 20 * np.exp(-(spec_diff**2) / 0.15)
                score += spec_score
            
            # LF/HF targeted matching
            if "lf_target" in t:
                lf_diff = abs(lf_total - t["lf_target"])
                score += 10 * np.exp(-(lf_diff**2) / 0.06)
                hf_diff = abs(hf_total - t["hf_target"])
                score += 6 * np.exp(-(hf_diff**2) / 0.05)
                mid_diff = abs((lmf_energy + 0.0) - t.get("mid_target", 0.3))
                score += 4 * np.exp(-(mid_diff**2) / 0.08)
            
            # Transient matching - enhanced
            if "global_transient" in t:
                trans_diff = abs(transient_est - t["global_transient"])
                score += 12 * np.exp(-(trans_diff**2) / 0.06)
                kick_diff = abs(onset - (0.25 + t["kick_transient"] * 0.9))
                score += 6 * np.exp(-(kick_diff**2) / 0.25)
            
            # Distortion matching
            if "dist_target" in t:
                dist_diff = abs(distortion_est - t["dist_target"])
                score += 8 * np.exp(-(dist_diff**2) / 0.05)
            
            # Loudness/dynamic matching
            if "loud_target" in t:
                loud_diff = abs(loudness_est - t["loud_target"])
                score += 6 * np.exp(-(loud_diff**2) / 0.07)
            
            # Spectral centroid + bandwidth matching (timbre)
            sc_target = t.get("sc_target", None)
            if sc_target is None:
                # Estimate from spectrum profile
                sc_target = 1500 + (hf_total - lf_total) * 3000
            sc_diff = abs(sc - sc_target)
            score += 8 * np.exp(-(sc_diff**2) / (2 * 1000**2))
            
            # Spectral contrast matching
            if "contrast_target" in t:
                contrast_diff = abs(contrast - t["contrast_target"])
                score += 5 * np.exp(-(contrast_diff**2) / 100)

        # Vocal score - enhanced
        vocal_diff = abs(vocal - t["vocal_prop"])
        score += t["vocal_weight"] * np.exp(-(vocal_diff**2) / 0.12)
        
        # Zero crossing rate matching (noisiness/percussiveness)
        zcr_target = 0.08 if t.get("parent_category") in dance_cats else 0.04
        zcr_diff = abs(zcr - zcr_target)
        score += 4 * np.exp(-(zcr_diff**2) / 0.01)
        
        # RMS energy matching
        rms_target = 0.15 if t.get("parent_category") in dance_cats else 0.08
        rms_diff = abs(rms - rms_target)
        score += 4 * np.exp(-(rms_diff**2) / 0.02)

        # Confidence bonus
        score += t["confidence_weight"]

        scores.append((score, i))
        if score > best_score:
            best_score = score
            best_idx = i

    # Sort and get top 3 for confidence calculation
    scores.sort(reverse=True, key=lambda x: x[0])
    top1_score = scores[0][0] if scores else 0
    top2_score = scores[1][0] if len(scores) > 1 else 0
    top3_score = scores[2][0] if len(scores) > 2 else 0
    confidence_gap = top1_score - top2_score
    # Additional confidence: how much top1 beats average of top2-5
    top5_avg = np.mean([s[0] for s in scores[:5]]) if len(scores) >= 5 else top2_score
    confidence_margin = top1_score - top5_avg

    best = GENRES[best_idx]
    ce, cc = CATS.get(best["parent_category"], ("Unknown", "未知"))

    # Metadata
    title = Path(filepath).stem
    artist = ""
    try:
        from mutagen import File as MutagenFile
        mf = MutagenFile(filepath)
        if mf and mf.tags:
            if "\xa9nam" in mf.tags:
                title = str(mf.tags["\xa9nam"][0])
            elif "TIT2" in mf.tags:
                title = str(mf.tags["TIT2"])
            if "\xa9ART" in mf.tags:
                artist = str(mf.tags["\xa9ART"][0])
            elif "TPE1" in mf.tags:
                artist = str(mf.tags["TPE1"])
    except Exception:
        pass

    # Calculate confidence based on score gap and margin
    base_confidence = 0.45
    gap_component = min(0.35, confidence_gap * 0.6)
    margin_component = min(0.20, confidence_margin * 0.3)
    confidence = min(0.98, max(0.25, base_confidence + gap_component + margin_component))

    # Top 3 genres
    top_genres = []
    for sc_val, idx in scores[:3]:
        g = GENRES[idx]
        top_genres.append({"genre": g["style_en"], "genre_cn": g["style_cn"], "score": round(sc_val, 2)})

    # Fusion genre detection: if top confidence < 0.6, likely fusion
    is_fusion = confidence < 0.6 and len(top_genres) >= 2
    fusion_label = ""
    if is_fusion:
        g1 = top_genres[0]["genre"]
        g2 = top_genres[1]["genre"]
        # Format fusion label: FirstLetter + Second
        fusion_label = f"{g1} / {g2}"
    
    result = {
        "file": filepath,
        "filename": Path(filepath).name,
        "song_info": {"title": title, "artist": artist},
        "bpm": bpm,
        "key": key,
        "genre": best["style_en"],
        "genre_cn": best["style_cn"],
        "genre_category": best["parent_category"],
        "genre_category_cn": cc,
        "confidence": round(confidence, 3),
        "is_fusion": is_fusion,
        "fusion_label": fusion_label,
        "fusion_genres": [top_genres[0]["genre"], top_genres[1]["genre"]] if is_fusion else [],
        "top_genres": top_genres,
        "duration_sec": round(full_duration, 2),
        "features": {
            "spectral_centroid": round(sc, 2),
            "spectral_rolloff": round(ro, 2),
            "zero_crossing_rate": round(zcr, 4),
            "onset_strength": round(onset, 4),
            "rms": round(rms, 4),
            "spectral_contrast": round(contrast, 2),
            "spectral_bandwidth": round(bw, 2),
            "vocal_estimate": round(vocal, 2),
            "distortion_estimate": round(distortion_est, 3),
            "transient_estimate": round(transient_est, 3),
            "subband_energy": {
                "sub": round(sub_energy, 3),
                "low": round(lf_energy, 3),
                "low_mid": round(lmf_energy, 3),
                "high_mid": round(hmf_energy, 3),
                "high": round(hf_energy, 3)
            }
        }
    }
    
    # Save result to cache for future use
    try:
        _save_features_to_cache(cache_key, result)
    except:
        pass
    
    return result



if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(analyze_audio(sys.argv[1]), indent=2, ensure_ascii=False))


# ============================================================
# Online / Network Features
# ============================================================

DEFAULT_GENRE_UPDATE_URL = "https://gist.githubusercontent.com/musictoolkit-pro/a1b2c3d4e5f6g7h8i9j0/raw/genres.json"
MUSICBRAINZ_API = "https://musicbrainz.org/ws/2/"
ACOUSTID_API = "https://api.acoustid.org/v2/lookup"
GENRE_LIB_VERSION = "10.12"


def check_network(timeout=5):
    """Check if internet connection is available."""
    import urllib.request
    try:
        urllib.request.urlopen("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False


def check_genre_update(current_version=None, update_url=None):
    """Check for genre library updates online.

    Returns:
        dict with keys: available (bool), version, count, url, message
    """
    import urllib.request
    url = update_url or DEFAULT_GENRE_UPDATE_URL
    try:
        # First check network
        if not check_network(timeout=5):
            return {"available": False, "message": "No internet connection. Using local genre library."}
        req = urllib.request.Request(url, headers={"User-Agent": "MusicToolkit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                new_count = len(data)
                current_count = len(GENRES)
                available = new_count > current_count
                return {
                    "available": available,
                    "remote_count": new_count,
                    "local_count": current_count,
                    "data": data,
                    "message": f"Update available: {new_count} genres (local: {current_count})" if available else f"Genre library is up to date ({current_count} genres)"
                }
    
            return {"available": False, "message": "Invalid update format"}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"available": False, "message": f"Genre library v{GENRE_LIB_VERSION} is up to date (remote server not configured yet)"}
        return {"available": False, "message": f"Update check failed: HTTP {e.code}"}
    except Exception as e:
        return {"available": False, "message": f"Update check failed: {str(e)}"}


def apply_genre_update(genre_data):
    """Apply downloaded genre data to local library.

    Args:
        genre_data: list of genre dicts from remote

    Returns:
        bool: success
    """
    global GENRES, _GENRE_TARGETS
    try:
        script_dir = Path(__file__).parent
        json_path = script_dir / "genres.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(genre_data, f, ensure_ascii=False, indent=2)
        GENRES = genre_data
        # Rebuild targets
        _GENRE_TARGETS = []
        for g in GENRES:
            is_detailed = g.get("data_quality") == "detailed"
            target = {
                "is_detailed": is_detailed,
                "bpm_min": g["bpm_min"],
                "bpm_max": g["bpm_max"],
                "bpm_mid": (g["bpm_min"] + g["bpm_max"]) / 2,
                "bpm_range": (g["bpm_max"] - g["bpm_min"]) / 2,
                "bpm_weight": 30 if is_detailed else 45,
                "vocal_prop": float(g.get("vocal_prop", 0.3)),
                "vocal_weight": 5 if is_detailed else 15,
                "confidence_weight": 2 * g.get("confidence_weight", 0.9),
            }
            if is_detailed and g.get("spectrum_profile"):
                sp = g["spectrum_profile"]
                target["lf_target"] = sp.get("sub_energy", 0) + sp.get("lf_energy", 0)
                target["hf_target"] = sp.get("hmf_energy", 0) + sp.get("hf_energy", 0)
            if is_detailed and g.get("transient_profile"):
                tp = g["transient_profile"]
                target["global_transient"] = tp.get("global_transient", 0.7)
                target["kick_transient"] = tp.get("kick_transient", 0.8)
            if is_detailed and g.get("distortion_profile"):
                dp = g["distortion_profile"]
                target["dist_target"] = max(0, min(1, 1 - dp.get("distortion_snr_db", 15) / 25))
            if is_detailed and g.get("dynamic_profile"):
                dynp = g["dynamic_profile"]
                target["loud_target"] = max(0, min(1, (dynp.get("loudness_target_lufs", -8) + 15) / 12))
            _GENRE_TARGETS.append(target)
        return True
    except Exception as e:
        print(f"Apply update failed: {e}")
        return False


def lookup_online_metadata(filepath, api_key=None):
    """Lookup track metadata online using MusicBrainz.

    Uses file metadata (title/artist) to search MusicBrainz for genre tags.

    Args:
        filepath: path to audio file
        api_key: optional AcoustID API key for fingerprint matching

    Returns:
        dict with online genre info or None
    """
    import urllib.request
    import urllib.parse
    try:
        # Get local metadata first
        title = Path(filepath).stem
        artist = ""
        try:
            from mutagen import File as MutagenFile
            mf = MutagenFile(filepath)
            if mf and mf.tags:
                if "\xa9nam" in mf.tags:
                    title = str(mf.tags["\xa9nam"][0])
                elif "TIT2" in mf.tags:
                    title = str(mf.tags["TIT2"])
                if "\xa9ART" in mf.tags:
                    artist = str(mf.tags["\xa9ART"][0])
                elif "TPE1" in mf.tags:
                    artist = str(mf.tags["TPE1"])
        except Exception:
            pass

        # Search MusicBrainz
        query_parts = []
        if title:
            query_parts.append(f'recording:"{urllib.parse.quote(title)}"')
        if artist:
            query_parts.append(f'artist:"{urllib.parse.quote(artist)}"')
        query = " AND ".join(query_parts) if query_parts else urllib.parse.quote(title)
        url = f"{MUSICBRAINZ_API}recording/?query={query}&fmt=json&limit=3"
        req = urllib.request.Request(url, headers={"User-Agent": "MusicToolkit/1.0 (contact@example.com)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            recordings = data.get("recordings", [])
            if recordings:
                rec = recordings[0]
                tags = [t.get("name", "") for t in rec.get("tags", [])]
                genres_online = [t for t in tags if t]
                return {
                    "title": rec.get("title", title),
                    "artist": rec.get("artist-credit", [{}])[0].get("name", artist) if rec.get("artist-credit") else artist,
                    "online_tags": genres_online,
                    "score": rec.get("score", 0),
                    "source": "musicbrainz"
                }
        return None
    except Exception as e:
        return {"error": str(e), "source": "musicbrainz"}


def match_genre_online(local_result, online_metadata):
    """Match local genre result with online metadata for improved accuracy.

    Args:
        local_result: result from analyze_audio()
        online_metadata: result from lookup_online_metadata()

    Returns:
        dict with matched genre info
    """
    if not online_metadata or "error" in online_metadata:
        return local_result

    online_tags = online_metadata.get("online_tags", [])
    if not online_tags:
        return local_result

    # Try to match online tags with local genre library
    matched_genre = None
    for tag in online_tags:
        tag_lower = tag.lower().replace(" ", "_").replace("-", "_")
        for g in GENRES:
            if g["style_en"].lower() == tag_lower or tag_lower in g["style_en"].lower():
                matched_genre = g
                break
        if matched_genre:
            break

    if matched_genre:
        result = dict(local_result)
        result["genre"] = matched_genre["style_en"]
        result["genre_cn"] = matched_genre["style_cn"]
        result["genre_category"] = matched_genre["parent_category"]
        result["online_matched"] = True
        result["online_source"] = online_metadata.get("source", "")
        result["confidence"] = min(0.99, local_result.get("confidence", 0.5) + 0.15)
        return result

    return local_result


def analyze_with_panns(filepath, top_n=3):
    """
    Try to use PANNs CNN14 enhanced analysis if available.
    Falls back to traditional analysis if PANNs not installed.
    """
    try:
        from analyze_panns import is_available, analyze_audio_style
        if is_available():
            result = analyze_audio_style(filepath, top_n=top_n)
            # Convert to standard format
            return {
                "file": filepath,
                "filename": Path(filepath).name,
                "song_info": {"title": Path(filepath).stem, "artist": ""},
                "bpm": result["bpm"],
                "key": "-",
                "genre": result["primary_genre"],
                "genre_cn": result["primary_genre_cn"],
                "genre_category": result.get("fusion_genres", [{}])[0].get("parent_category", "other") if result.get("fusion_genres") else "other",
                "genre_category_cn": "",
                "confidence": result["confidence"],
                "is_fusion": result["is_fusion"],
                "fusion_label": result.get("fusion_genres", [{}, {}])[0].get("style_en", "") + " / " + result.get("fusion_genres", [{}, {}])[1].get("style_en", "") if result["is_fusion"] else "",
                "top_genres": [{"genre": g["style_en"], "genre_cn": g["style_cn"], "score": g["confidence"]} for g in result["style_prediction_topN"]],
                "duration_sec": 0,
                "analyzer": "panns_cnn14",
                "features": result["audio_feature"]
            }
    except Exception as e:
        pass
    return None


def analyze_with_panns(filepath, top_n=3):
    """
    Try to use PANNs CNN14 enhanced analysis if available.
    Falls back to traditional analysis if PANNs not installed.
    """
    try:
        from analyze_panns import is_available, analyze_audio_style
        if is_available():
            result = analyze_audio_style(filepath, top_n=top_n)
            # Convert to standard format
            return {
                "file": filepath,
                "filename": Path(filepath).name,
                "song_info": {"title": Path(filepath).stem, "artist": ""},
                "bpm": result["bpm"],
                "key": "-",
                "genre": result["primary_genre"],
                "genre_cn": result["primary_genre_cn"],
                "genre_category": result.get("fusion_genres", [{}])[0].get("parent_category", "other") if result.get("fusion_genres") else "other",
                "genre_category_cn": "",
                "confidence": result["confidence"],
                "is_fusion": result["is_fusion"],
                "fusion_label": result.get("fusion_genres", [{}, {}])[0].get("style_en", "") + " / " + result.get("fusion_genres", [{}, {}])[1].get("style_en", "") if result["is_fusion"] else "",
                "top_genres": [{"genre": g["style_en"], "genre_cn": g["style_cn"], "score": g["confidence"]} for g in result["style_prediction_topN"]],
                "duration_sec": 0,
                "analyzer": "panns_cnn14",
                "features": result["audio_feature"]
            }
    except Exception as e:
        pass
    return None
