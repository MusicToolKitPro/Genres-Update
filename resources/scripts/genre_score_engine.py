"""
Genre Score Engine - Enhanced genre classification with multi-dimensional scoring.
Integrates with existing analyze_music.py for more accurate genre detection.
"""
import numpy as np


def calc_bpm_score(bpm: float, bpm_min: float, bpm_max: float) -> float:
    """BPM matching score: full score within range, linear decay outside."""
    if bpm_min <= bpm <= bpm_max:
        return 1.0
    if bpm < bpm_min:
        delta = bpm_min - bpm
        score = max(0, 1 - delta / 20)
    else:
        delta = bpm - bpm_max
        score = max(0, 1 - delta / 20)
    return score


def calc_spectrum_similarity(feat_spec: dict, ref_spec: dict) -> float:
    """Spectrum feature similarity, 0~1."""
    score_sum = 0.0
    cnt = 0
    for band_key in ref_spec:
        if band_key in feat_spec:
            ref_val = ref_spec[band_key]
            feat_val = feat_spec[band_key]
            diff = abs(ref_val - feat_val)
            s = max(0, 1 - diff)
            score_sum += s
            cnt += 1
    if cnt == 0:
        return 0.5
    return score_sum / cnt


# Enhanced genre reference library
GENRE_REF = [
    {
        "genre_name": "Hip Hop",
        "style_en": "hip_hop",
        "bpm_min": 70, "bpm_max": 115,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.8, "low_mid": 0.7, "mid": 0.6, "high_mid": 0.4, "high": 0.35},
        "ref_dynamic": {"compress": 0.4, "sidechain_strength": 0.2, "reverb_amount": 0.3},
        "valid_vocal": ["rap", "melody", "none"]
    },
    {
        "genre_name": "Rap",
        "style_en": "rap",
        "bpm_min": 70, "bpm_max": 115,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.8, "low_mid": 0.7, "mid": 0.75, "high_mid": 0.4, "high": 0.35},
        "ref_dynamic": {"compress": 0.6, "sidechain_strength": 0.2, "reverb_amount": 0.35},
        "valid_vocal": ["rap"]
    },
    {
        "genre_name": "Party Break",
        "style_en": "party_break",
        "bpm_min": 90, "bpm_max": 130,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.7, "low_mid": 0.6, "mid": 0.7, "high_mid": 0.65, "high": 0.6},
        "ref_dynamic": {"compress": 0.7, "sidechain_strength": 0.4, "reverb_amount": 0.4},
        "valid_vocal": ["rap", "mc", "melody", "none"]
    },
    {
        "genre_name": "Dirty Dutch",
        "style_en": "dirty_dutch",
        "bpm_min": 126, "bpm_max": 130,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.75, "low_mid": 0.4, "mid": 0.5, "high_mid": 0.85, "high": 0.7},
        "ref_dynamic": {"compress": 0.85, "sidechain_strength": 0.9, "reverb_amount": 0.45},
        "valid_vocal": ["none", "melody"]
    },
    {
        "genre_name": "Electro",
        "style_en": "electro",
        "bpm_min": 110, "bpm_max": 130,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.65, "low_mid": 0.5, "mid": 0.6, "high_mid": 0.7, "high": 0.55},
        "ref_dynamic": {"compress": 0.5, "sidechain_strength": 0.3, "reverb_amount": 0.38},
        "valid_vocal": ["none", "robot_talk", "rap"]
    },
    {
        "genre_name": "EDM",
        "style_en": "edm",
        "bpm_min": 126, "bpm_max": 132,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.8, "low_mid": 0.5, "mid": 0.55, "high_mid": 0.88, "high": 0.72},
        "ref_dynamic": {"compress": 0.9, "sidechain_strength": 0.92, "reverb_amount": 0.6},
        "valid_vocal": ["none", "melody"]
    },
    {
        "genre_name": "Trance",
        "style_en": "trance",
        "bpm_min": 130, "bpm_max": 142,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.6, "low_mid": 0.45, "mid": 0.5, "high_mid": 0.75, "high": 0.85},
        "ref_dynamic": {"compress": 0.6, "sidechain_strength": 0.5, "reverb_amount": 0.9},
        "valid_vocal": ["none", "melody"]
    },
    {
        "genre_name": "Bounce",
        "style_en": "bounce",
        "bpm_min": 125, "bpm_max": 142,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.72, "low_mid": 0.68, "mid": 0.55, "high_mid": 0.78, "high": 0.65},
        "ref_dynamic": {"compress": 0.82, "sidechain_strength": 0.85, "reverb_amount": 0.55},
        "valid_vocal": ["none", "melody", "chant"]
    },
    {
        "genre_name": "Melbourne Bounce",
        "style_en": "melbourne_bounce",
        "bpm_min": 126, "bpm_max": 130,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.70, "low_mid": 0.70, "mid": 0.52, "high_mid": 0.82, "high": 0.68},
        "ref_dynamic": {"compress": 0.85, "sidechain_strength": 0.88, "reverb_amount": 0.58},
        "valid_vocal": ["none", "chant"]
    },
    {
        "genre_name": "Bigroom House",
        "style_en": "bigroom_house",
        "bpm_min": 126, "bpm_max": 132,
        "time_signature": "4/4",
        "ref_spec": {"sub": 0.76, "low_mid": 0.45, "mid": 0.48, "high_mid": 0.86, "high": 0.75},
        "ref_dynamic": {"compress": 0.88, "sidechain_strength": 0.90, "reverb_amount": 0.72},
        "valid_vocal": ["none", "chant"]
    }
]


def convert_features_to_engine_format(audio_feature: dict) -> dict:
    """Convert existing analyze_music features to engine format."""
    # Extract spectrum from existing format
    sp = audio_feature.get("spectrum_profile", {}) or audio_feature.get("spectrum", {})
    
    # Map 6-band to 5-band engine format
    feat_spec = {
        "sub": sp.get("sub_energy", sp.get("sub", 0.5)),
        "low_mid": sp.get("lf_energy", sp.get("low_mid", 0.5)),
        "mid": sp.get("lmf_energy", sp.get("mid", 0.5)),
        "high_mid": sp.get("hmf_energy", sp.get("high_mid", 0.5)),
        "high": sp.get("hf_energy", sp.get("high", 0.5))
    }
    
    # Dynamic features
    dyn = audio_feature.get("dynamic_profile", {}) or {}
    peak_rms = dyn.get("peak_rms_ratio", 2.0)
    # Convert peak_rms_ratio to compress level (lower ratio = more compression)
    compress = max(0, min(1, (2.5 - peak_rms) / 1.5))
    
    # Sidechain strength from spectrum periodicity (approximate)
    sidechain = audio_feature.get("sidechain_strength", 0.3)
    
    # Reverb from transient (lower transient = more reverb)
    tr = audio_feature.get("transient_profile", {}) or {}
    global_transient = tr.get("global_transient", 0.6)
    reverb = max(0, min(1, 1 - global_transient))
    
    # Vocal type detection
    vocal_prop = audio_feature.get("vocal_prop", 0.5)
    if vocal_prop > 0.7:
        vocal_type = "melody"
    elif vocal_prop > 0.4:
        vocal_type = "rap"
    else:
        vocal_type = "none"
    
    return {
        "bpm": audio_feature.get("bpm", 128.0),
        "time_signature": audio_feature.get("time_signature", "4/4"),
        "spectrum": feat_spec,
        "dynamic_compress": compress,
        "sidechain_strength": sidechain,
        "reverb_amount": reverb,
        "vocal_type": vocal_type,
        "has_scratch": audio_feature.get("has_scratch", False),
        "has_cut_break": audio_feature.get("has_cut_break", False)
    }


def genre_score_engine(audio_feature: dict) -> list:
    """
    Main scoring entry point.
    Returns list of {"genre_name": "xxx", "style_en": "xxx", "score": 0~1} sorted descending.
    """
    # Convert features if needed
    if "spectrum_profile" in audio_feature or "dynamic_profile" in audio_feature:
        audio_feature = convert_features_to_engine_format(audio_feature)
    
    result = []
    bpm = audio_feature.get("bpm", 128.0)
    feat_spec = audio_feature.get("spectrum", {})
    feat_dyn_compress = audio_feature.get("dynamic_compress", 0.5)
    feat_sidechain = audio_feature.get("sidechain_strength", 0.3)
    feat_reverb = audio_feature.get("reverb_amount", 0.5)
    feat_vocal = audio_feature.get("vocal_type", "none")
    has_cut_break = audio_feature.get("has_cut_break", False)
    has_scratch = audio_feature.get("has_scratch", False)
    
    for g in GENRE_REF:
        # 1. BPM score
        s_bpm = calc_bpm_score(bpm, g["bpm_min"], g["bpm_max"])
        
        # 2. Time signature score
        s_time = 1.0 if audio_feature.get("time_signature", "4/4") == g["time_signature"] else 0.2
        
        # 3. Spectrum similarity
        s_spec = calc_spectrum_similarity(feat_spec, g["ref_spec"])
        
        # 4. Dynamic/timbre score
        d1 = max(0, 1 - abs(feat_dyn_compress - g["ref_dynamic"]["compress"]))
        d2 = max(0, 1 - abs(feat_sidechain - g["ref_dynamic"]["sidechain_strength"]))
        d3 = max(0, 1 - abs(feat_reverb - g["ref_dynamic"]["reverb_amount"]))
        s_dynamic = (d1 + d2 + d3) / 3
        
        # 5. Vocal matching score
        if feat_vocal in g["valid_vocal"]:
            s_vocal = 1.0
        else:
            s_vocal = 0.25
        
        # Special bonuses
        bonus = 0.0
        if g["genre_name"] == "Party Break":
            if has_cut_break or has_scratch:
                bonus += 0.12
        if g["genre_name"] == "Rap":
            if feat_vocal == "rap":
                bonus += 0.1
        
        # Weighted total score
        total = (
            0.30 * s_bpm +
            0.05 * s_time +
            0.30 * s_spec +
            0.20 * s_dynamic +
            0.15 * s_vocal
        )
        total = float(np.clip(total + bonus, 0, 1))
        result.append({
            "genre_name": g["genre_name"],
            "style_en": g["style_en"],
            "score": round(total, 4)
        })
    
    # Mutual exclusion penalty rules
    # If Melbourne Bounce score > 0.7, reduce Vina House score by 0.18
    # If Bigroom House score > 0.7, reduce Vina House score by 0.20
    # If Vina House score > 0.7, reduce Melbourne Bounce and Bigroom by 0.15
    melbourne_score = next((r["score"] for r in result if r["style_en"] == "melbourne_bounce"), 0)
    bigroom_score = next((r["score"] for r in result if r["style_en"] == "bigroom_house"), 0)
    vina_score = next((r["score"] for r in result if r["style_en"] == "vina_house"), 0)
    partybreak_score = next((r["score"] for r in result if r["style_en"] == "party_break"), 0)
    
    for r in result:
        if r["style_en"] == "vina_house":
            if melbourne_score > 0.7:
                r["score"] = max(0, r["score"] - 0.18)
            if bigroom_score > 0.7:
                r["score"] = max(0, r["score"] - 0.20)
            # Party Break vs Vina House: breakbeat vs continuous 4/4 kick
            if partybreak_score > 0.65:
                r["score"] = max(0, r["score"] - 0.25)
        elif r["style_en"] in ("melbourne_bounce", "bigroom_house"):
            if vina_score > 0.7:
                r["score"] = max(0, r["score"] - 0.15)
        elif r["style_en"] == "party_break":
            if vina_score > 0.65:
                r["score"] = max(0, r["score"] - 0.20)
    
    # Sort by score descending
    result.sort(key=lambda x: x["score"], reverse=True)
    return result


if __name__ == "__main__":
    # Test
    test_feat = {
        "bpm": 100.0,
        "time_signature": "4/4",
        "spectrum": {"sub": 0.8, "low_mid": 0.7, "mid": 0.6, "high_mid": 0.4, "high": 0.35},
        "dynamic_compress": 0.5,
        "sidechain_strength": 0.2,
        "reverb_amount": 0.3,
        "vocal_type": "rap"
    }
    results = genre_score_engine(test_feat)
    for r in results:
        print(f"  {r['genre_name']:15s}: {r['score']:.4f}")
