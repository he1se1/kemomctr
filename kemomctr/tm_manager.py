import os
import json
from pathlib import Path

def build_translation_memory(ref_dir, source_lang, target_lang, format_id="json"):
    """
    参照ディレクトリ(旧Ver)を走査し、
    { "source Text": "target Text" } の形式でメモリ上に辞書を構築する。
    """
    tm = {}
    ref_path = Path(ref_dir)
    
    if not ref_path.exists():
        print(f"[警告] 参照ディレクトリが見つかりません: {ref_dir}")
        return {}

    print(f"  -> 翻訳メモリを構築中... (参照: {ref_dir})")
    
    from . import format_handlers
    handler = format_handlers.get_handler_by_id(format_id)
    if not handler:
        print(f"[警告] 非対応のフォーマット '{format_id}' が指定されたため、TM構築スキップします。")
        return {}
    
    file_count = 0
    
    for root, dirs, files in os.walk(ref_path):
        for file in files:
            if handler.is_source_file(file, source_lang):
                target_filename = handler.get_target_filename(file, target_lang)
                if target_filename in files:
                    src_full = os.path.join(root, file)
                    tgt_full = os.path.join(root, target_filename)
                    
                    try:
                        src_data = handler.read(src_full)
                        tgt_data = handler.read(tgt_full)
                        
                        if not src_data or not tgt_data:
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

    print(f"  -> メモリ構築完了: {len(tm)} 件を登録しました (ファイル数: {file_count})")
    return tm