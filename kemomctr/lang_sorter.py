import re
from collections import defaultdict

ANCHOR_PREFIXES = (
    "block.", "item.", "fluid.", "entity.", "enchantment.", "effect.", "biome."
)
STOPWORDS = {
    "tooltip", "desc", "description", "line", "info", "jei", "name", 
    "subtitle", "title", "lang"
}

def _is_valid_token(token):
    if re.match(r'^-?\d+$', token): return False
    if re.match(r'^[0-9a-fA-F]{8,}$', token) and not token.isalpha(): return False
    if token.lower() in STOPWORDS: return False
    return True

def _natural_sort_key(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

# lang_sorter.py の末尾の関数を置き換え

def get_clustered_missing_keys(source_data, missing_keys):
    """
    アンカーごとにまとめたキーのリストのリスト（クラスター群）を返す
    """
    anchor_ids = set()
    for key in source_data.keys():
        if key.startswith(ANCHOR_PREFIXES):
            tokens = key.split('.')
            core_id = tokens[-1]
            if _is_valid_token(core_id):
                anchor_ids.add(core_id)

    anchor_clusters = defaultdict(list)
    unanchored_keys = []

    for key in missing_keys:
        tokens = key.split('.')
        matched_anchor = None
        for token in sorted(tokens, key=len, reverse=True):
            if token in anchor_ids:
                matched_anchor = token
                break
        
        if matched_anchor:
            anchor_clusters[matched_anchor].append(key)
        else:
            unanchored_keys.append(key)

    clusters = []
    anchors = sorted(anchor_clusters.keys(), key=_natural_sort_key)
    
    for anchor in anchors:
        keys_in_cluster = sorted(
            anchor_clusters[anchor], 
            key=lambda k: (len(k.split('.')), _natural_sort_key(k))
        )
        if keys_in_cluster:
            clusters.append(keys_in_cluster)

    if unanchored_keys:
        clusters.append(sorted(unanchored_keys, key=_natural_sort_key))

    return clusters