import os
import json
from pathlib import Path

def build_translation_memory(ref_dir, source_lang, target_lang):
    """
    参照ディレクトリ(旧Ver)を走査し、
    { "English Text": "Japanese Text" } の形式でメモリ上に辞書を構築する。
    """
    tm = {}
    ref_path = Path(ref_dir)
    
    if not ref_path.exists():
        print(f"[警告] 参照ディレクトリが見つかりません: {ref_dir}")
        return {}

    print(f"  -> 翻訳メモリを構築中... (参照: {ref_dir})")
    
    source_filename = f"{source_lang}.json"
    target_filename = f"{target_lang}.json"
    
    file_count = 0
    
    for root, dirs, files in os.walk(ref_path):
        if source_filename in files and target_filename in files:
            src_full = os.path.join(root, source_filename)
            tgt_full = os.path.join(root, target_filename)
            
            try:
                with open(src_full, 'r', encoding='utf-8') as f:
                    src_data = json.load(f)
                with open(tgt_full, 'r', encoding='utf-8') as f:
                    tgt_data = json.load(f)
                
                if not isinstance(src_data, dict) or not isinstance(tgt_data, dict):
                    continue

                # ペアになるキーを探して辞書に登録
                for key, src_text in src_data.items():
                    if key in tgt_data:
                        tgt_text = tgt_data[key]
                        if src_text and tgt_text and src_text not in tm:
                            tm[src_text] = tgt_text
                
                file_count += 1
            except Exception:
                # 読み込みエラーは無視して次へ
                continue

    print(f"  -> メモリ構築完了: {len(tm)} 件のフレーズを学習しました (ファイル数: {file_count})")
    return tm