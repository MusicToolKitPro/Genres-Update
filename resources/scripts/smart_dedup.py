#!/usr/bin/env python3
"""Smart deduplication for audio files - Optimized version.
Uses grouping strategy to reduce O(n²) to near O(n).
"""
import re
import subprocess
CREATE_NO_WINDOW = 0x08000000
import json
from pathlib import Path
from collections import defaultdict

# Version suffix patterns (case insensitive)
VERSION_PATTERNS = [
    r'\b(radio\s*edit|radio\s*mix|radio\s*version)\b',
    r'\b(extended\s*mix|extended\s*version|ext\.?\s*mix)\b',
    r'\b(original\s*mix|original\s*version|orig\.?\s*mix)\b',
    r'\b(club\s*mix|club\s*edit|club\s*version)\b',
    r'\b(dub\s*mix|dub\s*version)\b',
    r'\b(instrumental|inst\.?)\b',
    r'\b(acapella|vocal\s*mix)\b',
    r'\b(remix|rework|re-edit|bootleg|flip|mashup|mash\s*up)\b',
    r'\b(remastered|remaster)\b',
    r'\b(live|concert|acoustic|unplugged)\b',
    r'\b(demo|preview|snippet)\b',
    r'\b(clean|explicit|dirty)\b',
    r'\b(feat\.?|ft\.?|featuring)\b',
    r'\b(vs\.?|x|&)\b',
    r'\b([A-Z][a-z]+)\s+(remix|edit|mix|rework)\b',
    r'\b(19|20)\d{2}\b',
    r'\[.*?\]',
    r'\(.*?\)',
]

def parse_filename(filename):
    """Parse filename into base name, version info, and artist."""
    stem = Path(filename).stem
    
    artist = ""
    title_part = stem
    if ' - ' in stem:
        parts = stem.split(' - ', 1)
        if len(parts[0]) < 60 and len(parts[1]) < 100:
            artist = parts[0].strip()
            title_part = parts[1].strip()
    
    version_parts = []
    cleaned = title_part
    
    for pattern in VERSION_PATTERNS:
        matches = re.findall(pattern, cleaned, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0] if m[0] else ''
            if m and m.strip():
                version_parts.append(m.strip())
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    cleaned = re.sub(r'[\s_-]+', ' ', cleaned).strip(' -_')
    cleaned = cleaned.strip('.,;:!?')
    
    version = ' '.join(version_parts).strip()
    version = re.sub(r'\s+', ' ', version).strip()
    
    # Normalized base name for grouping
    norm_base = re.sub(r'[^a-z0-9]+', '', cleaned.lower())
    
    return {
        'base_name': cleaned.lower(),
        'norm_base': norm_base,
        'version': version,
        'norm_version': re.sub(r'[^a-z0-9]+', '', version.lower()),
        'artist': artist,
        'norm_artist': re.sub(r'[^a-z0-9]+', '', artist.lower()),
        'full_stem': stem,
        'is_versioned': bool(version),
        'original_stem': stem,
    }

def get_audio_quality(filepath):
    """Get audio quality metrics using ffprobe."""
    result = {
        'bit_rate': 0, 'sample_rate': 0, 'channels': 0,
        'duration': 0, 'codec': '', 'format': '',
        'file_size': 0, 'quality_score': 0,
    }
    
    try:
        p = Path(filepath)
        if not p.exists():
            return result
        result['file_size'] = p.stat().st_size
        
        ffprobe_path = None
        import sys
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                candidate = Path(sys._MEIPASS) / 'ffmpeg' / 'ffprobe.exe'
                if candidate.exists():
                    ffprobe_path = str(candidate)
            if not ffprobe_path:
                candidate = Path(sys.executable).parent / 'ffmpeg' / 'ffprobe.exe'
                if candidate.exists():
                    ffprobe_path = str(candidate)
        
        if not ffprobe_path:
            import shutil
            ffprobe_path = shutil.which('ffprobe')
        
        if not ffprobe_path:
            ext = p.suffix.lower()
            if ext in ('.flac', '.wav'):
                result['quality_score'] = 90
            elif ext in ('.m4a', '.aac'):
                result['quality_score'] = 70
            elif ext == '.mp3':
                result['quality_score'] = 60
            else:
                result['quality_score'] = 50
            return result
        
        cmd = [ffprobe_path, '-v', 'quiet', '-print_format', 'json',
               '-show_format', '-show_streams', str(filepath)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, creationflags=CREATE_NO_WINDOW)
        if proc.returncode != 0:
            return result
        
        data = json.loads(proc.stdout)
        fmt = data.get('format', {})
        result['bit_rate'] = int(fmt.get('bit_rate', 0))
        result['duration'] = float(fmt.get('duration', 0))
        result['format'] = fmt.get('format_name', '')
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                result['sample_rate'] = int(stream.get('sample_rate', 0))
                result['channels'] = int(stream.get('channels', 0))
                result['codec'] = stream.get('codec_name', '')
                break
        
        score = 0.0
        br = result['bit_rate']
        if br >= 1411200: score += 40
        elif br >= 320000: score += 35
        elif br >= 256000: score += 30
        elif br >= 192000: score += 25
        elif br >= 128000: score += 18
        elif br > 0: score += 10
        
        sr = result['sample_rate']
        if sr >= 96000: score += 20
        elif sr >= 48000: score += 18
        elif sr >= 44100: score += 15
        elif sr > 0: score += 10
        
        ch = result['channels']
        if ch >= 6: score += 10
        elif ch >= 2: score += 8
        elif ch > 0: score += 5
        
        dur = result['duration']
        if dur >= 180: score += 15
        elif dur >= 120: score += 12
        elif dur >= 60: score += 8
        elif dur > 0: score += 4
        
        codec = result['codec'].lower()
        if codec in ('flac', 'pcm_s16le', 'pcm_s24le', 'alac'): score += 15
        elif codec in ('aac',): score += 12
        elif codec == 'mp3': score += 10
        elif codec: score += 8
        
        result['quality_score'] = min(100.0, score)
    except Exception:
        pass
    
    return result

def is_same_song_parsed(p1, p2):
    """Check if two parsed filenames are the same song."""
    n1 = p1['norm_base']
    n2 = p2['norm_base']
    
    base_match = False
    if n1 and n2:
        if n1 == n2:
            base_match = True
        elif len(n1) > 10 and len(n2) > 10:
            if n1 in n2 or n2 in n1:
                base_match = True
            else:
                common = sum(1 for a, b in zip(n1, n2) if a == b)
                similarity = common / max(len(n1), len(n2))
                if similarity > 0.85:
                    base_match = True
    
    a1 = p1['norm_artist']
    a2 = p2['norm_artist']
    artist_match = False
    if a1 and a2:
        if a1 == a2 or a1 in a2 or a2 in a1:
            artist_match = True
    
    same_version = (p1['norm_version'] == p2['norm_version']) if (p1['norm_version'] or p2['norm_version']) else True
    is_same = base_match and (artist_match or not p1['norm_artist'] or not p2['norm_artist'])
    
    return is_same, same_version

def smart_dedup(file_list, existing_files=None):
    """Optimized smart deduplication using grouping strategy."""
    existing_files = existing_files or []
    
    result = {
        'to_add': [], 'duplicates': [],
        'same_song_diff_version': [], 'same_song_same_version': [],
        'replaced': [],
    }
    
    # Step 1: Remove exact path duplicates
    seen_paths = set()
    unique_new = []
    for f in file_list:
        try:
            key = str(Path(f).resolve()).lower()
        except:
            key = str(f).lower()
        if key in seen_paths:
            result['duplicates'].append(f)
        else:
            seen_paths.add(key)
            unique_new.append(f)
    
    # Step 2: Check against existing files
    existing_resolved = set()
    for ef in existing_files:
        try:
            existing_resolved.add(str(Path(ef).resolve()).lower())
        except:
            existing_resolved.add(str(ef).lower())
    
    not_duplicate = []
    for f in unique_new:
        try:
            key = str(Path(f).resolve()).lower()
        except:
            key = str(f).lower()
        if key in existing_resolved:
            result['duplicates'].append(f)
        else:
            not_duplicate.append(f)
    
    if not not_duplicate:
        return result
    
    # Step 3: Parse all files (fast)
    parsed_new = [(f, parse_filename(f)) for f in not_duplicate]
    parsed_existing = [(f, parse_filename(f)) for f in existing_files]
    
    # Step 4: Group by first 8 chars of normalized base name
    groups = defaultdict(list)
    for idx, (f, p) in enumerate(parsed_new):
        group_key = p['norm_base'][:8] if p['norm_base'] else '__unknown__'
        groups[group_key].append(idx)
    
    # Also group existing files
    existing_groups = defaultdict(list)
    for idx, (f, p) in enumerate(parsed_existing):
        group_key = p['norm_base'][:8] if p['norm_base'] else '__unknown__'
        existing_groups[group_key].append(idx)
    
    # Step 5: Process each group
    to_add = []
    skip_indices = set()
    
    for group_key, indices in groups.items():
        if not indices:
            continue
        
        # Find same songs within this group (much smaller comparison)
        group_song_clusters = []
        processed_in_group = set()
        
        for i_pos, i in enumerate(indices):
            if i in skip_indices or i in processed_in_group:
                continue
            
            f1, p1 = parsed_new[i]
            cluster = [i]
            processed_in_group.add(i)
            
            # Compare with others in same group
            for j in indices[i_pos+1:]:
                if j in skip_indices or j in processed_in_group:
                    continue
                f2, p2 = parsed_new[j]
                is_same, _ = is_same_song_parsed(p1, p2)
                if is_same:
                    cluster.append(j)
                    processed_in_group.add(j)
            
            # Check against existing files in same group
            existing_same = []
            for ej in existing_groups.get(group_key, []):
                ef, ep = parsed_existing[ej]
                is_same, _ = is_same_song_parsed(p1, ep)
                if is_same:
                    existing_same.append(ej)
            
            if len(cluster) > 1 or existing_same:
                # Separate by version
                version_groups = defaultdict(list)
                for idx in cluster:
                    f, p = parsed_new[idx]
                    vkey = p['norm_version'] or 'original'
                    version_groups[vkey].append(idx)
                
                for vkey, v_indices in version_groups.items():
                    if len(v_indices) == 1:
                        idx = v_indices[0]
                        to_add.append(parsed_new[idx][0])
                        if vkey != 'original':
                            result['same_song_diff_version'].append(parsed_new[idx][0])
                    else:
                        # Multiple files same version - pick best quality
                        best_idx = None
                        best_score = -1
                        for idx in v_indices:
                            f = parsed_new[idx][0]
                            q = get_audio_quality(f)
                            if q['quality_score'] > best_score:
                                best_score = q['quality_score']
                                best_idx = idx
                        
                        if best_idx is not None:
                            to_add.append(parsed_new[best_idx][0])
                            skipped = [parsed_new[idx][0] for idx in v_indices if idx != best_idx]
                            result['same_song_same_version'].append({
                                'kept': parsed_new[best_idx][0],
                                'skipped': skipped,
                                'version': vkey,
                            })
                            for idx in v_indices:
                                if idx != best_idx:
                                    skip_indices.add(idx)
            else:
                # No same song found
                to_add.append(f1)
    
    result['to_add'] = to_add
    return result

if __name__ == '__main__':
    import time
    import random
    
    print("Testing optimized smart_dedup...")
    
    # Generate test files
    artists = ["Artist A", "Artist B", "DJ X", "Producer Z"]
    titles = [f"Song Title {i}" for i in range(200)]
    versions = ["", "(Radio Edit)", "(Extended Mix)", "(DJ Remix)", "(Remastered)"]
    
    test_files = []
    random.seed(42)
    for i in range(2000):
        artist = random.choice(artists)
        title = random.choice(titles)
        version = random.choice(versions)
        ext = random.choice([".mp3", ".wav", ".flac"])
        if version:
            test_files.append(f"C:\\Test\\{artist} - {title} {version}{ext}")
        else:
            test_files.append(f"C:\\Test\\{artist} - {title}{ext}")
    
    print(f"Generated {len(test_files)} test files")
    
    start = time.time()
    result = smart_dedup(test_files, [])
    elapsed = time.time() - start
    
    print(f"\nResults:")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Speed: {len(test_files)/elapsed:.0f} files/second")
    print(f"  To add: {len(result['to_add'])}")
    print(f"  Duplicates: {len(result['duplicates'])}")
    print(f"  Same song diff version: {len(result['same_song_diff_version'])}")
    print(f"  Same song same version: {len(result['same_song_same_version'])}")
    print(f"  Estimated time for 10,000: {elapsed*5:.2f}s")
