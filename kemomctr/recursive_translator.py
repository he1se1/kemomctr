import os
import sys
import csv
from pathlib import Path
from google import genai

from . import single_translator
from . import tm_manager

API_KEY = os.getenv("GOOGLE_API_KEY")

def load_glossary(csv_path, source_lang, target_lang):
    """CSVから用語集を読み込み、指定された言語ペアの辞書を返す"""
    if not csv_path:
        return {}
    if not os.path.exists(csv_path):
        print(f"[警告] 用語集ファイルが見つかりません: {csv_path}")
        return {}

    glossary = {}
    try:
        # utf-8-sigを使うことで、Excel等で出力したBOM付きCSVも安全に読める
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # 必要なカラムが存在するかチェック
            if not reader.fieldnames or source_lang not in reader.fieldnames or target_lang not in reader.fieldnames:
                print(f"[警告] CSVに '{source_lang}' または '{target_lang}' の列が存在しません。用語集は適用されません。")
                return {}

            for row in reader:
                src_val = row.get(source_lang, "").strip()
                tgt_val = row.get(target_lang, "").strip()
                
                # 両方のカラムに値が入っている場合のみ追加
                if src_val and tgt_val:
                    glossary[src_val] = tgt_val
                    
        print(f"  -> 用語集({source_lang} -> {target_lang})を {len(glossary)} 件読み込みました。")
    except Exception as e:
        print(f"[エラー] 用語集の読み込みに失敗しました: {e}")
        
    return glossary

def run_recursive(target_dir, source_lang="en_us", target_lang="ja_jp", glossary_path=None, ref_dir=None):
    if not API_KEY:
        print("エラー: 環境変数 GEMINI_KEY が設定されていません。")
        sys.exit(1)

    client = genai.Client(api_key=API_KEY)
    target_path = Path(target_dir)
    source_filename = f"{source_lang}.json"
    target_filename = f"{target_lang}.json"

    if not target_path.exists():
        print(f"エラー: ディレクトリが見つかりません: {target_dir}")
        return

    print(f"=== kemomctr: 翻訳モード (tr) ===")
    print(f"探索: {target_dir}")
    print(f"設定: {source_filename} -> {target_filename}")
    
    glossary = load_glossary(glossary_path, source_lang, target_lang)

    # ▼▼▼ 翻訳メモリの構築 ▼▼▼
    translation_memory = {}
    if ref_dir:
        translation_memory = tm_manager.build_translation_memory(ref_dir, source_lang, target_lang)

    print("ヒント: 実行中に Ctrl+C を押すと途中経過を保存して安全に終了します。")

    try:
        for root, dirs, files in os.walk(target_path):
            if os.path.basename(root) == 'lang' and source_filename in files:
                src_path_full = os.path.join(root, source_filename)
                tgt_path_full = os.path.join(root, target_filename)
                
                # memory を渡す
                interrupted = single_translator.process_single_file(
                    client=client,
                    src_path_full=src_path_full,
                    tgt_path_full=tgt_path_full,
                    target_dir=target_dir,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    glossary=glossary,
                    translation_memory=translation_memory # ▼ 追加
                )
                
                if interrupted:
                    print("\nプログラムを終了します。")
                    sys.exit(0)
                    
    except KeyboardInterrupt:
        print("\n[!] 探索中に中断されました。終了します。")
        sys.exit(0)