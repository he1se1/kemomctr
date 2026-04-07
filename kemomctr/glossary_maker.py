import os
import json
import csv
from pathlib import Path

# これから始まるキーは名詞（ゲーム内オブジェクト）とする
NOUN_PREFIXES = (
    "item.",
    "block.",
    "entity.",
    "enchantment.",
    "effect.",
    "biome.",
    "fluid."
)

def load_existing_glossary(csv_path):
    """既存のGlossaryを行単位の辞書のリストとしてロードし、フィールド名を返す"""
    glossary_rows = []
    fieldnames = []
    if not os.path.exists(csv_path):
        return glossary_rows, fieldnames
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                fieldnames = list(reader.fieldnames)
            for row in reader:
                glossary_rows.append(dict(row))
    except Exception:
        pass
    return glossary_rows, fieldnames

def update_or_add_row(glossary_rows, src_lang, src_text, tgt_lang, tgt_text):
    for row in glossary_rows:
        match = False
        if src_lang in row and row[src_lang] == src_text and src_text != "":
            match = True
        if tgt_lang in row and row[tgt_lang] == tgt_text and tgt_text != "":
            match = True
            
        if match:
            updated = False
            # 既存の行に言語の列が無く、今回新しく追加できる場合
            if src_text and not row.get(src_lang):
                row[src_lang] = src_text
                updated = True
            if tgt_text and not row.get(tgt_lang):
                row[tgt_lang] = tgt_text
                updated = True
            return updated, False # updated_existing (bool), added_new (bool)
            
    # 見つからなかった場合は新規行
    new_row = {src_lang: src_text}
    if tgt_text:
        new_row[tgt_lang] = tgt_text
    glossary_rows.append(new_row)
    return False, True

def run_glossary_maker(src_dir, tgt_dir, output_csv, source_lang="en_us", target_lang="ja_jp", format_id="json"):
    src_path = Path(src_dir)
    tgt_path = Path(tgt_dir) if tgt_dir else None
    
    from . import format_handlers
    handler = format_handlers.get_handler_by_id(format_id)
    if not handler:
        print(f"エラー: 非対応のフォーマット '{format_id}' が指定されました。")
        return

    if not src_path.exists():
        print(f"エラー: ソースディレクトリが見つかりません: {src_dir}")
        return

    if not output_csv:
        output_csv = "glossary_generated.csv"

    print(f"=== kemomctr: 用語集自動生成モード (glos) ===")
    print(f"ソース探索: {src_dir}")
    if tgt_dir:
        print(f"ターゲット探索: {tgt_dir}")
    print(f"抽出フォーマット: {format_id} (キー接頭辞ベース)")
    
    # 既存のものがあれば読み込む
    glossary_rows, fieldnames = load_existing_glossary(output_csv)
    
    if source_lang not in fieldnames:
        fieldnames.append(source_lang)
    if target_lang not in fieldnames:
        fieldnames.append(target_lang)

    initial_count = len(glossary_rows)
    if initial_count > 0:
        print(f"  -> 既存の用語集 ({output_csv}) から {initial_count} 件をロードしました。")

    file_count = 0
    added_count = 0
    updated_count = 0
    
    for root, dirs, files in os.walk(src_path):
        for file in files:
            if handler.is_source_file(file, source_lang):
                src_full = os.path.join(root, file)
                rel_path = os.path.relpath(root, src_dir)
                
                try:
                    src_data = handler.read(src_full)
                    
                    tgt_data = {}
                    if tgt_path and tgt_path.exists():
                        target_filename = handler.get_target_filename(file, target_lang)
                        tgt_full = os.path.join(tgt_path, rel_path, target_filename)
                        if os.path.exists(tgt_full):
                            try:
                                data = handler.read(tgt_full)
                                if isinstance(data, dict):
                                    tgt_data = data
                            except Exception:
                                pass
                    
                    if not isinstance(src_data, dict):
                        continue

                    for key, src_text in src_data.items():
                        if isinstance(key, str) and key.startswith(NOUN_PREFIXES):
                            tgt_text = tgt_data.get(key, "")
                            
                            updated, added = update_or_add_row(glossary_rows, source_lang, src_text, target_lang, tgt_text)
                            if updated:
                                updated_count += 1
                            if added:
                                added_count += 1

                    file_count += 1
                except Exception as e:
                    print(f"[警告] ファイル読み込みエラー ({src_full}): {e}")

    print(f"  -> {file_count}個のファイルから走査完了。新規行追加: {added_count}件, 既存行への多言語追記: {updated_count}件")

    try:
        # UTF-8 with BOMで書き出し
        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # primary keyはとりあえずsource_langでソート
            sorted_rows = sorted(glossary_rows, key=lambda r: r.get(source_lang, ""))
            writer.writerows(sorted_rows)
                
        print(f"  -> 用語集を保存・上書きしました: {output_csv}")
    except Exception as e:
        print(f"[エラー] 用語集の保存に失敗しました: {e}")
