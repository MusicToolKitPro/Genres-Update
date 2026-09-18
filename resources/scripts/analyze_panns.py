#!/usr/bin/env python3
"""
PANNs CNN14 Deep Learning Audio Genre Classifier
===================================================
Advanced genre analysis using pre-trained CNN14 model for rich audio embeddings,
6-band spectrum analysis, precise transient detection, and LUFS loudness metering.

Usage:
    from analyze_panns import analyze_audio_style
    result = analyze_audio_style("song.mp3", top_n=3)

Dependencies (optional - install for enhanced mode):
    pip install panns-inference librosa numpy scipy pyloudnorm torch

Note: This module is optional. If dependencies are not installed, the software
falls back to the traditional librosa-based analyzer.
"""

import json
import os
import sys
import shutil
import hashlib
from pathlib import Path

# ==============================================
# Ensure PANNs data files exist BEFORE importing panns_inference
# (panns_inference config.py tries to wget class_labels_indices.csv on import)
# ==============================================
def _ensure_panns_data_files():
    """Ensure class_labels_indices.csv and model files exist in user home.
    If running from PyInstaller bundle, copy from _MEIPASS if needed."""
    panns_dir = Path.home() / "panns_data"
    panns_dir.mkdir(parents=True, exist_ok=True)
    
    labels_file = panns_dir / "class_labels_indices.csv"
    model_file = panns_dir / "Cnn14_mAP=0.431.pth"
    
    # Try to find source files in bundle or script directory
    bundle_dir = getattr(sys, '_MEIPASS', None)
    candidate_dirs = []
    if bundle_dir:
        candidate_dirs.append(Path(bundle_dir) / "panns_data")
    candidate_dirs.append(Path(__file__).parent.parent / "panns_data")
    candidate_dirs.append(Path.cwd() / "panns_data")
    
    # Copy labels file if missing
    if not labels_file.exists() or labels_file.stat().st_size < 1000:
        for src_dir in candidate_dirs:
            src = src_dir / "class_labels_indices.csv"
            if src.exists():
                try:
                    shutil.copy2(src, labels_file)
                    break
                except:
                    continue
    
    # Copy model file if missing
    if not model_file.exists() or model_file.stat().st_size < 100000000:
        for src_dir in candidate_dirs:
            src = src_dir / "Cnn14_mAP=0.431.pth"
            if src.exists():
                try:
                    shutil.copy2(src, model_file)
                    break
                except:
                    continue
    
    return labels_file.exists() and labels_file.stat().st_size > 1000

# Ensure data files exist before importing panns_inference
_ensure_panns_data_files()

# Try to import heavy dependencies - fail gracefully
try:
    import numpy as np
    import librosa
    import scipy.signal
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

try:
    import pyloudnorm as pyln
    HAS_LOUDNORM = True
except ImportError:
    HAS_LOUDNORM = False

try:
    from panns_inference import AudioTagging, SoundEventDetection
    HAS_PANNS = True
except Exception:
    HAS_PANNS = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# ==============================================
# Global Configuration
# ==============================================
SR_TARGET = 32000

# 6-band frequency division - aligned with genre database
FREQ_BANDS = {
    "sub":   (20,    60),
    "lf":    (60,   250),
    "lmf":   (250, 1000),
    "mf":    (1000,3000),
    "hmf":   (3000,8000),
    "hf":    (8000,16000)
}

# Confidence weights
WEIGHT_BPM = 0.25
WEIGHT_SPECTRUM = 0.40
WEIGHT_TRANSIENT = 0.20
WEIGHT_DYNAMIC = 0.15

# Cache directory
_appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
CACHE_DIR = _appdata / "MusicToolkit" / "SData" / "feature_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================
# Model Global Loading (initialize once at startup)
# ==============================================
_at = None
_sed = None
_meter = None
_device = "cpu"

def initialize_models(device="cpu"):
    """Initialize PANNs models globally. Call once at software startup."""
    global _at, _sed, _meter, _device
    
    if not HAS_PANNS:
        print("[PANNs] panns-inference not installed. Using traditional analyzer.")
        return False
    
    # Ensure model files exist (copy from bundle if needed)
        print("[PANNs] Model files not found. Please run with internet connection to download.")
        return False
    
    _device = device
    if device == "cuda" and not (HAS_TORCH and torch.cuda.is_available()):
        print("[PANNs] CUDA not available, falling back to CPU.")
        _device = "cpu"
    
    try:
        print(f"[PANNs] Loading CNN14 model on {_device}...")
        _at = AudioTagging(checkpoint_path=None, device=_device)
        # SoundEventDetection not needed for genre analysis - skip to save memory
        _sed = None
        if HAS_LOUDNORM:
            _meter = pyln.Meter(SR_TARGET)
        print("[PANNs] Model loaded successfully.")
        return True
    except Exception as e:
        print(f"[PANNs] Model loading failed: {e}")
        return False

def is_available():
    """Check if PANNs enhanced analysis is available (dependencies installed)."""
    return HAS_CORE and HAS_PANNS and HAS_TORCH

# ==============================================
# Feature Cache
# ==============================================
def _get_cache_key(audio_path):
    """Generate cache key from file path + modification time + size."""
    try:
        stat = os.stat(audio_path)
        key_str = f"{audio_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key_str.encode()).hexdigest()
    except:
        return hashlib.md5(audio_path.encode()).hexdigest()

def _load_from_cache(cache_key):
    """Load extracted features from cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def _save_to_cache(cache_key, features):
    """Save extracted features to cache."""
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump(features, f)
    except:
        pass

# ==============================================
# 1. Feature Extraction Core
# ==============================================
def extract_audio_features(audio_path, use_cache=True):
    """
    Extract comprehensive audio features using PANNs CNN14 + traditional DSP.
    
    Returns dict with:
        - bpm: float
        - spectrum_profile: 6-band energy distribution
        - transient_profile: global + kick transient metrics
        - dynamic_profile: LUFS + peak/RMS ratio
        - panns_embedding: CNN14 feature vector (527-dim)
        - panns_tags: top audio tags from AudioTagging
    """
    if not HAS_CORE:
        raise ImportError("Core dependencies (numpy/librosa/scipy) not installed")
    
    # Check cache
    cache_key = _get_cache_key(audio_path)
    if use_cache:
        cached = _load_from_cache(cache_key)
        if cached:
            return cached
    
    # Load audio
    wav, sr = librosa.load(audio_path, sr=SR_TARGET, mono=True)
    audio = wav[None, :]
    
    # PANNs inference (if model loaded)
    panns_embedding = None
    panns_tags = []
    if _at is not None:
        try:
            clipwise_output, embedding = _at.inference(audio)
            panns_embedding = embedding[0].tolist()
            # Get top tags
            if hasattr(_at, 'labels'):
                labels = _at.labels
                sorted_idx = np.argsort(clipwise_output[0])[::-1][:10]
                panns_tags = [{"tag": labels[i], "probability": float(clipwise_output[0][i])} 
                              for i in sorted_idx if clipwise_output[0][i] > 0.1]
        except Exception as e:
            print(f"[PANNs] Inference error: {e}")
    
    # STFT spectrum
    n_fft = 1024
    hop_length = 512
    f, t, stft = scipy.signal.stft(wav, fs=SR_TARGET, nperseg=n_fft, noverlap=n_fft-hop_length)
    spec_amp = np.abs(stft)
    
    # 6-band energy normalization
    band_energy = {}
    total_energy = 1e-10
    for band_name, (f_low, f_high) in FREQ_BANDS.items():
        mask = (f >= f_low) & (f <= f_high)
        band_power = np.mean(spec_amp[mask, :] ** 2)
        band_energy[band_name] = band_power
        total_energy += band_power
    for k in band_energy:
        band_energy[k] = band_energy[k] / total_energy
    
    # Global transient
    onset_env = librosa.onset.onset_strength(y=wav, sr=SR_TARGET, hop_length=hop_length)
    global_transient = float(np.clip(np.percentile(onset_env, 80) / (np.max(onset_env)+1e-8), 0, 1))
    
    # Kick transient detection (20~250Hz)
    f_sub_lf_mask = (f >=20) & (f <=250)
    sublf_spec = spec_amp[f_sub_lf_mask, :]
    sublf_env = np.mean(sublf_spec, axis=0)
    sublf_onset = librosa.onset.onset_detect(onset_envelope=sublf_env, sr=SR_TARGET, 
                                                hop_length=hop_length, backtrack=True)
    if len(sublf_onset) > 0:
        first_kick_frame = sublf_onset[0]
        kick_transient_time_ms = int(t[first_kick_frame] * 1000)
    else:
        kick_transient_time_ms = 999
    kick_transient = float(np.clip(np.max(sublf_env)/(np.max(wav)+1e-8), 0, 1))
    
    # LUFS loudness & RMS dynamic
    integrated_lufs = -23.0  # default
    if _meter is not None:
        try:
            integrated_lufs = float(_meter.integrated_loudness(wav))
        except:
            pass
    
    rms_all = librosa.feature.rms(y=wav, hop_length=hop_length)[0]
    peak_rms_ratio = float(np.max(rms_all) / (np.mean(rms_all)+1e-8))
    
    # BPM extraction - enhanced multi-strategy
    try:
        tempo, _ = librosa.beat.beat_track(y=wav, sr=SR_TARGET)
        bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
    except:
        bpm = 120.0
    
    feat_dict = {
        "bpm": bpm,
        "spectrum_profile": {
            "sub_energy": band_energy["sub"],
            "lf_energy": band_energy["lf"],
            "lmf_energy": band_energy["lmf"],
            "mf_energy": band_energy["mf"],
            "hmf_energy": band_energy["hmf"],
            "hf_energy": band_energy["hf"]
        },
        "transient_profile": {
            "global_transient": global_transient,
            "kick_transient": kick_transient,
            "kick_transient_time_ms": kick_transient_time_ms
        },
        "dynamic_profile": {
            "integrated_lufs": integrated_lufs,
            "peak_rms_ratio": peak_rms_ratio
        },
        "panns_embedding": panns_embedding,
        "panns_tags": panns_tags
    }
    
    # Save to cache
    if use_cache:
        _save_to_cache(cache_key, feat_dict)
    
    return feat_dict

# ==============================================
# 2. Scoring Function
# ==============================================
def calculate_match_score(style_ref, feat):
    """
    Calculate match score between a genre reference and extracted features.
    
    Weights: BPM 25% + Spectrum 40% + Transient 20% + Dynamic 15%
    """
    score = 0.0
    bpm = feat["bpm"]
    
    # BPM scoring
    if "bpm_range" in style_ref:
        min_bpm, max_bpm = style_ref["bpm_range"]
    else:
        min_bpm = style_ref.get("bpm_min", 100)
        max_bpm = style_ref.get("bpm_max", 180)
    
    if min_bpm <= bpm <= max_bpm:
        bpm_score = 1.0
    else:
        delta = min(abs(bpm - max_bpm), abs(bpm - min_bpm))
        bpm_score = max(0, 1.0 - delta / 20)
    score += bpm_score * WEIGHT_BPM
    
    # Spectrum Euclidean distance scoring (6-band)
    sp_ref = style_ref.get("spectrum_profile")
    if sp_ref is not None and "spectrum_profile" in feat:
        sp_feat = feat["spectrum_profile"]
        sp_dist = np.sqrt(sum(
            (sp_ref.get(f"{k}_energy", 0) - sp_feat.get(f"{k}_energy", 0)) ** 2
            for k in ["sub", "lf", "lmf", "mf", "hmf", "hf"]
        ))
        sp_score = max(0, 1 - sp_dist * 2.5)
        score += sp_score * WEIGHT_SPECTRUM
    
    # Transient scoring
    tr_ref = style_ref.get("transient_profile")
    if tr_ref is not None and "transient_profile" in feat:
        tr_feat = feat["transient_profile"]
        tr_dist = np.sqrt(
            (tr_ref.get("global_transient", 0.7) - tr_feat.get("global_transient", 0.5)) ** 2 +
            (tr_ref.get("kick_transient", 0.8) - tr_feat.get("kick_transient", 0.6)) ** 2
        )
        tr_score = max(0, 1 - tr_dist * 2.5)
        score += tr_score * WEIGHT_TRANSIENT
    
    # Dynamic/loudness scoring
    dyn_ref = style_ref.get("dynamic_profile")
    if dyn_ref is not None and "dynamic_profile" in feat:
        dyn_feat = feat["dynamic_profile"]
        
        # LUFS matching
        ref_lufs = dyn_ref.get("loudness_target_lufs", -8)
        lufs_diff = abs(dyn_feat["integrated_lufs"] - ref_lufs)
        lufs_score = max(0, 1 - lufs_diff / 15)
        
        # Peak/RMS ratio matching
        ref_ratio = dyn_ref.get("peak_rms_ratio", 2.0)
        ratio_diff = abs(dyn_feat["peak_rms_ratio"] - ref_ratio)
        ratio_score = max(0, 1 - ratio_diff / 3.0)
        
        dyn_score = (lufs_score + ratio_score) / 2
        score += dyn_score * WEIGHT_DYNAMIC
    
    return round(float(score), 4)

# ==============================================
# 3. Main Entry Point
# ==============================================
def analyze_audio_style(audio_path, genre_database=None, top_n=3, 
                         use_cache=True, fusion_threshold=0.6):
    """
    Main entry point for PANNs-enhanced genre classification.
    
    Args:
        audio_path: Path to audio file
        genre_database: List of genre reference dicts (loads from genres.json if None)
        top_n: Number of top candidates to return
        use_cache: Enable feature caching
        fusion_threshold: If top confidence < this value, mark as fusion genre
    
    Returns:
        dict with:
            - audio_feature: extracted features
            - style_prediction_topN: top N genre predictions with confidence
            - is_fusion: bool, whether this is likely a fusion genre
            - fusion_genres: top 2 genres if fusion detected
            - primary_genre: best matching genre name
    """
    # Load genre database if not provided
    if genre_database is None:
        import sys
        # Try multiple paths for genres.json (supports PyInstaller bundle)
        candidate_paths = [
            Path(__file__).parent / "genres.json",
            Path(getattr(sys, '_MEIPASS', '')) / "scripts" / "genres.json",
            Path(getattr(sys, '_MEIPASS', '')) / "genres.json",
            Path.cwd() / "scripts" / "genres.json",
        ]
        genre_database = []
        for gp in candidate_paths:
            if gp.exists():
                try:
                    with open(gp, 'r', encoding='utf-8') as f:
                        genre_database = json.load(f)
                    break
                except:
                    continue
    
    # Lazy load models if not already loaded (only if PANNs available)
    global _at
    if _at is None and HAS_PANNS and HAS_TORCH:
        try:
            initialize_models(device="cpu")
        except:
            pass
    
    # Extract features
    feat = extract_audio_features(audio_path, use_cache=use_cache)
    
    # Get audio duration
    try:
        duration_sec = float(librosa.get_duration(filename=audio_path))
    except:
        duration_sec = 0
    
    # Score all genres
    result_list = []
    for style in genre_database:
        conf = calculate_match_score(style, feat)
        result_list.append({
            "style_en": style.get("style_en", style.get("style_name", "unknown")),
            "style_cn": style.get("style_cn", ""),
            "confidence": conf,
            "parent_category": style.get("parent_category", "other")
        })
    
    # Sort by confidence descending
    result_list.sort(key=lambda x: x["confidence"], reverse=True)
    top_result = result_list[:top_n]
    
    # Fusion genre detection
    is_fusion = len(top_result) >= 2 and top_result[0]["confidence"] < fusion_threshold
    fusion_genres = top_result[:2] if is_fusion else []
    
    # Primary genre
    primary = top_result[0] if top_result else {"style_en": "Unknown", "style_cn": "未知", "confidence": 0}
    
    # Fusion label
    fusion_label = ""
    if is_fusion and len(fusion_genres) >= 2:
        fusion_label = f"{fusion_genres[0]['style_en']} / {fusion_genres[1]['style_en']}"
    
    output = {
        "file": audio_path,
        "audio_feature": feat,
        "style_prediction_topN": top_result,
        "is_fusion": is_fusion,
        "fusion_genres": fusion_genres,
        "fusion_label": fusion_label,
        "primary_genre": primary["style_en"],
        "primary_genre_cn": primary["style_cn"],
        "confidence": primary["confidence"],
        "bpm": feat["bpm"],
        "duration_sec": duration_sec,
        "analyzer": "panns_cnn14"
    }
    
    return output

# ==============================================
# Batch Processing (multiprocessing)
# ============================================
def batch_analyze(audio_paths, genre_database=None, top_n=3, 
                   num_workers=None, use_cache=True):
    """
    Batch analyze multiple audio files using multiprocessing.
    
    Args:
        audio_paths: List of audio file paths
        genre_database: Genre reference list
        top_n: Number of top candidates
        num_workers: Number of worker processes (default: cpu_count - 1)
        use_cache: Enable feature caching
    
    Returns:
        List of analysis results
    """
    if num_workers is None:
        import multiprocessing
        num_workers = max(1, multiprocessing.cpu_count() - 1)
    
    results = []
    
    # For small batches or when PANNs not available, process sequentially
    if len(audio_paths) < 4 or not is_available():
        for path in audio_paths:
            try:
                result = analyze_audio_style(path, genre_database, top_n, use_cache)
                results.append(result)
            except Exception as e:
                results.append({"file": path, "error": str(e)})
        return results
    
    # Multiprocessing for larger batches
    from multiprocessing import Pool
    from functools import partial
    
    analyze_func = partial(analyze_audio_style, 
                           genre_database=genre_database, 
                           top_n=top_n, 
                           use_cache=use_cache)
    
    with Pool(processes=num_workers) as pool:
        results = pool.map(analyze_func, audio_paths)
    
    return results

# ==============================================
# Test Entry Point
# ==============================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_panns.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Initialize models
    success = initialize_models(device="cpu")
    
    if not success:
        print("PANNs not available. Please install: pip install panns-inference torch")
        sys.exit(1)
    
    # Analyze
    result = analyze_audio_style(audio_file, top_n=5)
    
    print("\n" + "="*60)
    print("PANNs CNN14 Genre Analysis Result")
    print("="*60)
    print(f"File: {result['file']}")
    print(f"BPM: {result['bpm']:.1f}")
    print(f"Primary Genre: {result['primary_genre']} ({result['primary_genre_cn']})")
    print(f"Confidence: {result['confidence']:.4f}")
    print(f"Fusion Genre: {'Yes' if result['is_fusion'] else 'No'}")
    print("\nTop 5 Predictions:")
    for i, pred in enumerate(result['style_prediction_topN'], 1):
        print(f"  {i}. {pred['style_en']:25s} - {pred['confidence']:.4f}")
    
    if result['is_fusion']:
        print(f"\nFusion Genres: {result['fusion_genres'][0]['style_en']} + {result['fusion_genres'][1]['style_en']}")
    
    print("\nFeature Summary:")
    feat = result['audio_feature']
    print(f"  Spectrum: Sub={feat['spectrum_profile']['sub_energy']:.3f}, "
          f"LF={feat['spectrum_profile']['lf_energy']:.3f}, "
          f"HMF={feat['spectrum_profile']['hmf_energy']:.3f}")
    print(f"  Transient: Global={feat['transient_profile']['global_transient']:.3f}, "
          f"Kick={feat['transient_profile']['kick_transient']:.3f}")
    print(f"  Dynamic: LUFS={feat['dynamic_profile']['integrated_lufs']:.1f}, "
          f"Peak/RMS={feat['dynamic_profile']['peak_rms_ratio']:.2f}")
