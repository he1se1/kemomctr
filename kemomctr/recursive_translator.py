"""
再帰翻訳モジュール
指定されたディレクトリ以下のファイルを走査し、翻訳処理を実行する
"""

import os
import sys
import csv
from pathlib import Path
from google import genai

from . import single_translator
from . import tm_manager
from . import format_handlers

API_KEY = os.getenv("GOOGLE_API_KEY")

def load_glossary(csv_path, source_lang, target_lang):
    """
    CSVファイルから用語集を読み込む
    
    Args:
        csv_path (str): 用語集CSVのパス
        source_lang (str): 翻訳元の言語コード (例: en_us)
        target_lang (str): 翻訳先の言語コード (例: ja_jp)
        
    Returns:
        dict: {原文: 訳文} の辞書。読み込み失敗時は空辞書を返す。
    """
    if not csv_path:
        return {}
    if not os.path.exists(csv_path):
        print(f"[警告] 用語集ファイルが見つかりません: {csv_path}")
        return {}

    glossary = {}
    try:
        # UTF-8 with BOM に対応
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # 必要なカラムの存在確認
            if not reader.fieldnames or source_lang not in reader.fieldnames or target_lang not in reader.fieldnames:
                print(f"[警告] CSVに '{source_lang}' または '{target_lang}' の列が存在しません。")
                return {}

            for row in reader:
                src_val = row.get(source_lang, "").strip()
                tgt_val = row.get(target_lang, "").strip()
                
                if src_val and tgt_val:
                    glossary[src_val] = tgt_val
                    
        print(f"  -> 用語集({source_lang} -> {target_lang})を {len(glossary)} 件読み込みました。")
    except Exception as e:
        print(f"[エラー] 用語集の読み込みに失敗しました: {e}")
        
    return glossary

def run_recursive(target_dir, source_lang="en_us", target_lang="ja_jp", glossary_path=None, ref_dir=None, no_sort=False, format_id="json", custom_system_instruction=None):
    """
    指定ディレクトリ内を再帰的に探索し、各ファイルの翻訳を行う
    
    Args:
        target_dir (str): 探索対象のルートディレクトリ
        source_lang (str): 元言語
        target_lang (str): 先言語
        glossary_path (str, optional): 用語集のパス
        ref_dir (str, optional): 翻訳メモリ用の旧バージョンディレクトリ
        no_sort (bool): キーのソートを行わず元の順序で処理するか
        format_id (str): 対象フォーマットID (json, lang, snbt)
        custom_system_instruction (str, optional): カスタムプロンプト
    """
    if not API_KEY:
        print("エラー: 環境変数 GOOGLE_API_KEY が設定されていません。")
        sys.exit(1)

    client = genai.Client(api_key=API_KEY)
    target_path = Path(target_dir)

    if not target_path.exists():
        print(f"エラー: ディレクトリが見つかりません: {target_dir}")
        return

    # フォーマットハンドラの取得
    handler = format_handlers.get_handler_by_id(format_id)
    if not handler:
        print(f"エラー: 非対応のフォーマット '{format_id}' が指定されました。")
        return

    print(f"=== kemomctr: 翻訳モード (tr) ===")
    print(f"探索: {target_dir}")
    print(f"設定: {source_lang} -> {target_lang} (フォーマット: {format_id})")
    
    glossary = load_glossary(glossary_path, source_lang, target_lang)

    # 翻訳メモリ(TM)の構築
    translation_memory = {}
    if ref_dir:
        translation_memory = tm_manager.build_translation_memory(ref_dir, source_lang, target_lang)

    try:
        # ディレクトリ内を再帰的に探索
        for root, dirs, files in os.walk(target_path):
            # Minecraft Mod の慣習として lang ディレクトリ内を対象とする
            dirname = os.path.basename(root).lower()
            if dirname == "lang":
                for file in files:
                    if handler.is_source_file(file, source_lang):
                        src_path_full = os.path.join(root, file)
                        target_filename = handler.get_target_filename(file, target_lang)
                        tgt_path_full = os.path.join(root, target_filename)
                        
                        # 個別ファイルの処理を実行
                        interrupted = single_translator.process_single_file(
                            client=client,
                            src_path_full=src_path_full,
                            tgt_path_full=tgt_path_full,
                            target_dir=target_dir,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            glossary=glossary,
                            translation_memory=translation_memory,
                            no_sort=no_sort,
                            handler=handler,
                            custom_system_instruction=custom_system_instruction
                        )
                        
                        if interrupted:
                            print("\nプログラムを停止します。")
                            return
                    
    except KeyboardInterrupt:
        print("\n[!] 中断されました。終了します。")
        return