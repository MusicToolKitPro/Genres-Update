"""
Filename Genre Parser - Extract genre hints from audio filenames.
Matches genre names (English/Chinese) and tags from the genre database.
"""
import json
import re
from pathlib import Path


class FilenameGenreParser:
    """Parse audio filenames to extract genre hints."""
    
    def __init__(self, genres_path=None):
        """Initialize with genre database."""
        if genres_path is None:
            # Try to find genres.json relative to this script
            genres_path = Path(__file__).parent / "genres.json"
        
        self.genres = []
        self.keyword_map = {}  # keyword -> (style_en, style_cn, weight)
        
        try:
            with open(genres_path, 'r', encoding='utf-8') as f:
                self.genres = json.load(f)
            self._build_keyword_map()
        except Exception as e:
            print(f"FilenameGenreParser: Could not load genres: {e}")
    
    def _build_keyword_map(self):
        """Build keyword mapping from genre names and tags."""
        for g in self.genres:
            style_en = g.get('style_en', '')
            style_cn = g.get('style_cn', '')
            tags = g.get('tags', [])
            confidence = g.get('confidence_weight', 0.8)
            
            # Add English name (split by underscore for partial matching)
            if style_en:
                # Full name
                self._add_keyword(style_en.lower(), style_en, style_cn, confidence * 0.9)
                # Parts of name (e.g., "vina_house" -> "vina", "house")
                parts = style_en.split('_')
                if len(parts) > 1:
                    for part in parts:
                        if len(part) > 2:  # Skip very short words
                            self._add_keyword(part.lower(), style_en, style_cn, confidence * 0.4)
            
            # Add Chinese name
            if style_cn:
                # Extract Chinese genre name (remove English part in parentheses)
                cn_clean = re.sub(r'[（(].*?[)）]', '', style_cn).strip()
                if cn_clean and len(cn_clean) >= 2:
                    self._add_keyword(cn_clean.lower(), style_en, style_cn, confidence * 0.95)
            
            # Add tags
            for tag in tags:
                if tag and len(tag) > 2:
                    self._add_keyword(tag.lower(), style_en, style_cn, confidence * 0.6)
    
    def _add_keyword(self, keyword, style_en, style_cn, weight):
        """Add keyword to map, keeping highest weight."""
        if not keyword:
            return
        if keyword not in self.keyword_map or weight > self.keyword_map[keyword][2]:
            self.keyword_map[keyword] = (style_en, style_cn, weight)
    
    def parse_filename(self, filename):
        """
        Parse filename and extract genre hints.
        
        Args:
            filename: Audio file name (with or without extension)
        
        Returns:
            dict or None: {
                'style_en': 'vina_house',
                'style_cn': '越南鼓 Vina House',
                'confidence': 0.85,
                'matched_keywords': ['vina', 'house'],
                'source': 'filename'
            }
            Returns None if no genre keywords found.
        """
        if not filename:
            return None
        
        # Remove extension
        name = Path(filename).stem.lower()
        
        # Remove common non-genre patterns
        # Remove version info (Radio Edit, Extended Mix, Remix, etc.)
        name_clean = re.sub(r'\b(radio edit|extended mix|original mix|remix|edit|mix|version|ver|feat|ft|dj|official|audio|video|hd|hq|mp3|flac|wav)\b', ' ', name)
        # Remove year patterns
        name_clean = re.sub(r'\b(19|20)\d{2}\b', ' ', name_clean)
        # Remove BPM patterns
        name_clean = re.sub(r'\b\d{2,3}\s*bpm\b', ' ', name_clean)
        # Remove special characters
        name_clean = re.sub(r'[_\-\[\]\(\)\{\}\.,!@#\$%\^&\*\+=~`\?/\\\|]', ' ', name_clean)
        # Normalize whitespace
        name_clean = re.sub(r'\s+', ' ', name_clean).strip()
        
        # Expand common concatenated genre names (e.g., "partybreak" -> "party break")
        concatenated_genres = [
            ('partybreak', 'party break'),
            ('party-break', 'party break'),
            ('hiphop', 'hip hop'),
            ('hip-hop', 'hip hop'),
            ('drumandbass', 'drum and bass'),
            ('drum&bass', 'drum and bass'),
            ('dnb', 'drum and bass'),
            ('rnb', 'r and b'),
            ('edmtrap', 'edm trap'),
            ('trapedm', 'edm trap'),
            ('hardstyle', 'hard style'),
            ('hardtechno', 'hard techno'),
            ('deephouse', 'deep house'),
            ('techhouse', 'tech house'),
            ('acidhouse', 'acid house'),
            ('electrohouse', 'electro house'),
            ('bigroom', 'big room'),
            ('melodictechno', 'melodic techno'),
            ('liquidfunk', 'liquid funk'),
            ('neurofunk', 'neuro funk'),
            ('jumpup', 'jump up'),
            ('vinahouse', 'vina house'),
            ('thai breakbeat', 'thai breakbeat'),
        ]
        for concat, expanded in concatenated_genres:
            name_clean = re.sub(r'\b' + re.escape(concat) + r'\b', expanded, name_clean, flags=re.IGNORECASE)
        
        if not name_clean:
            return None
        
        # Find matching keywords (with word boundary matching to prevent substring matches)
        matches = []
        matched_keywords = []
        
        for keyword, (style_en, style_cn, weight) in self.keyword_map.items():
            # Use word boundary matching for English keywords
            # This prevents "trap" from matching "rap" as substring
            if re.search(r'\b' + re.escape(keyword) + r'\b', name_clean, re.IGNORECASE):
                matches.append({
                    'style_en': style_en,
                    'style_cn': style_cn,
                    'weight': weight,
                    'keyword': keyword
                })
                matched_keywords.append(keyword)
            # For Chinese keywords, use simple substring (Chinese doesn't have word boundaries)
            elif any('\u4e00' <= c <= '\u9fff' for c in keyword) and keyword in name_clean:
                matches.append({
                    'style_en': style_en,
                    'style_cn': style_cn,
                    'weight': weight,
                    'keyword': keyword
                })
                matched_keywords.append(keyword)
        
        if not matches:
            return None
        
        # Aggregate matches by style_en
        genre_scores = {}
        for m in matches:
            en = m['style_en']
            if en not in genre_scores:
                genre_scores[en] = {
                    'style_en': en,
                    'style_cn': m['style_cn'],
                    'total_weight': 0,
                    'matched_keywords': []
                }
            genre_scores[en]['total_weight'] += m['weight']
            genre_scores[en]['matched_keywords'].append(m['keyword'])
        
        # Sort by total weight
        sorted_genres = sorted(genre_scores.values(), key=lambda x: x['total_weight'], reverse=True)
        
        # Get top match
        top = sorted_genres[0]
        
        # Calculate confidence (cap at 0.95, more keywords = higher confidence)
        num_keywords = len(set(top['matched_keywords']))
        confidence = min(0.95, top['total_weight'] * (0.7 + 0.1 * num_keywords))
        
        return {
            'style_en': top['style_en'],
            'style_cn': top['style_cn'],
            'confidence': round(confidence, 4),
            'matched_keywords': list(set(top['matched_keywords'])),
            'all_matches': [
                {
                    'style_en': g['style_en'],
                    'style_cn': g['style_cn'],
                    'score': round(g['total_weight'], 4)
                }
                for g in sorted_genres[:5]
            ],
            'source': 'filename'
        }
    
    def parse_filepath(self, filepath):
        """Parse full file path (uses filename only)."""
        return self.parse_filename(Path(filepath).name)


# Global singleton instance
_parser_instance = None

def get_parser(genres_path=None):
    """Get or create global parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = FilenameGenreParser(genres_path)
    return _parser_instance


def parse_filename_genre(filename, genres_path=None):
    """Convenience function to parse genre from filename."""
    parser = get_parser(genres_path)
    return parser.parse_filename(filename)


if __name__ == "__main__":
    # Test
    test_files = [
        "DJ Soda - Vina House Mix 2024.mp3",
        "Hardstyle Festival Mix 2024 (150 BPM).flac",
        "Hip Hop Classics - Best Rap Songs.wav",
        "Melbourne Bounce Mix - DJ Will Sparks.mp3",
        "Bigroom House Festival EDM Mix.flac",
        "Thai Breakbeat 泰鼓摇 Mix 2024.mp3",
        "Unknown Song - Artist Name.mp3",
        "Trance Classics - Best of 2000s.wav",
        "EDM Party Mix - Electro House.flac",
        "Amapiano South Africa Mix 2024.mp3"
    ]
    
    parser = FilenameGenreParser()
    print(f"Loaded {len(parser.genres)} genres, {len(parser.keyword_map)} keywords\n")
    
    for f in test_files:
        result = parser.parse_filename(f)
        if result:
            print(f"  {f[:50]:50s} -> {result['style_en']:20s} ({result['confidence']:.2f}) [keywords: {result['matched_keywords']}]")
        else:
            print(f"  {f[:50]:50s} -> No genre found (will use audio detection)")
