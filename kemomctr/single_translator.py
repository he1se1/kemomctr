"""
個別ファイル翻訳モジュール
単一の言語ファイルに対して翻訳リクエストをチャンクに分けて発行する
"""

import os
import json
import time
from google.genai import types

# GUI連携・中断制御用のグローバル変数
CANCEL_REQUESTED = False
current_thread = None

# 翻訳設定
MODEL_NAME = os.getenv("KEMOMCTR_MODEL", "gemini-3-flash-preview")
BATCH_SIZE = 50          # 1リクエストあたりの最大キー数
MAX_BATCH_CHARS = 3000   # 1リクエストあたりの最大文字数

# 言語コードと表示名のマッピング
LANG_NAME_MAP = {
    "en_us": "English", "ja_jp": "Japanese",
    "zh_cn": "Chinese (Simplified)", "zh_tw": "Chinese (Traditional)",
    "ko_kr": "Korean", "ru_ru": "Russian",
    "fr_fr": "French", "de_de": "German", "es_es": "Spanish"
}

def get_lang_name(code):
    """言語コードを表示用の名称に変換する"""
    return LANG_NAME_MAP.get(code.lower(), code)

def normalize_response(result):
    """
    LLMからのレスポンスを標準的な辞書形式に正規化する
    
    様々な出力形式(リスト、ネストされた辞書など)を
    { "key": "value" } のフラットな辞書に変換を試みる
    """
    if isinstance(result, dict):
        if len(result) == 1:
            first_val = list(result.values())[0]
            if isinstance(first_val, dict): return first_val
            if isinstance(first_val, list):
                new_dict = {}
                for item in first_val:
                    if isinstance(item, dict) and "key" in item and "value" in item:
                        new_dict[item["key"]] = item["value"]
                return new_dict
        return result
    elif isinstance(result, list):
        new_dict = {}
        for item in result:
            if isinstance(item, dict):
                if "key" in item and "value" in item:
                    new_dict[item["key"]] = item["value"]
                else:
                    new_dict.update(item)
        return new_dict
    return None
    
def _clean_json_text(text):
    """
    レスポンスからMarkdown装飾(```json等)を剥ぎ取り、純粋なJSON文字列にする
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start_idx = 1 if lines[0].startswith("```") else 0
        end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start_idx:end_idx]).strip()
    return text

def _create_system_instruction(s_name, t_name, filtered_glossary, custom_instr=None):
    """
    Geminiに与えるシステムプロンプトを作成する
    """
    if custom_instr:
        # カスタム命令がある場合はプレースホルダを置換
        instr = custom_instr
        instr = instr.replace("{{s_name}}", s_name)
        instr = instr.replace("{{t_name}}", t_name)
        instr = instr.replace("{{glossary}}", json.dumps(filtered_glossary, ensure_ascii=False))
        return instr
    
    return f"""
        You are a professional translator for Minecraft Mods.
        Translate the JSON values from {s_name} to {t_name}.

        # Output Format Rules
        1. Output strictly a FLAT JSON Object: {{ "original_key": "translated_value" }}.
        2. Do NOT use a list or array.
        3. Do NOT wrap the result in keys like "translations".

        # Translation Rules
        1. Preserve format specifiers exactly (%s, %d, %.1f).
        2. Do NOT translate technical keys.
        3. Use the Glossary provided below.
        4. Context: Modded Minecraft Gaming.
        5. Multi-line Handling: If the value contains newlines (\\n), treat it as a single cohesive text. Preserve the number of lines and the positions of empty lines.
        
        # Glossary
        {json.dumps(filtered_glossary, ensure_ascii=False)}
        """

def translate_chunk(client, chunk_data, chunk_index, total_chunks, source_lang, target_lang, glossary, custom_system_instruction=None):
    """
    特定のチャンクデータをAPIで翻訳する。
    エラー時にはチャンクを分割してリトライを試みる。
    """
    s_name = get_lang_name(source_lang)
    t_name = get_lang_name(target_lang)

    # 用語集の絞り込み (チャンク内のテキストに含まれるもののみ)
    filtered_glossary = {}
    if glossary:
        chunk_text_lower = " ".join(str(v) for v in chunk_data.values()).lower()
        for term, translation in glossary.items():
            if term.lower() in chunk_text_lower:
                filtered_glossary[term] = translation

    if filtered_glossary:
        print(f" (用語集ヒット: {len(filtered_glossary)}件)")

    system_instruction = _create_system_instruction(s_name, t_name, filtered_glossary, custom_system_instruction)
    prompt_text = f"Translate these entries:\n{json.dumps(chunk_data, ensure_ascii=False)}"

    try:
        print(f"    - Batch {chunk_index}/{total_chunks} ({len(chunk_data)}項目) 処理中...", end="", flush=True)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        
        text = _clean_json_text(response.text)
        raw_result = json.loads(text)
        final_dict = normalize_response(raw_result)
        
        if final_dict is None:
            raise ValueError("データ抽出失敗 (形式不正)")
        
        print(" OK")
        return final_dict
        
    except Exception as e:
        # 1つ以上のデータがある場合は、チャンクを2分割して再試行
        if len(chunk_data) > 1:
            print(f" -> エラー発生({e})。バッチを分割して再試行します... (サイズ: {len(chunk_data)} -> {len(chunk_data)//2})")
            items = list(chunk_data.items())
            mid = len(items) // 2
            res1 = translate_chunk(client, dict(items[:mid]), chunk_index, total_chunks, source_lang, target_lang, glossary, custom_system_instruction)
            res2 = translate_chunk(client, dict(items[mid:]), chunk_index, total_chunks, source_lang, target_lang, glossary, custom_system_instruction)
            
            combined = {}
            if res1: combined.update(res1)
            if res2: combined.update(res2)
            return combined
        else:
            print(f" 失敗: {e}")
            return None

def create_chunks(data_map, no_sort=False, src_path=""):
    """
    翻訳データをバッチサイズや文字数制限に基づきチャンク(分割単位)に分ける
    """
    path_lower = src_path.lower()
    is_quest_path = "quest" in path_lower
    skip_sort = no_sort or is_quest_path

    chunks = []
    
    if skip_sort:
        # ソートせず、出現順にパッキング
        reason = "[--no-sort] 指定あり" if no_sort else "クエストファイルを検知"
        print(f"  -> {reason}: オリジナルの順序を維持してバッチ処理します")
        
        current_chunk = {}
        current_chars = 0
        for k, v in data_map.items():
            v_len = len(str(v))
            if (len(current_chunk) >= BATCH_SIZE) or (current_chunk and current_chars + v_len > MAX_BATCH_CHARS):
                chunks.append(current_chunk)
                current_chunk = {}
                current_chars = 0
            current_chunk[k] = v
            current_chars += v_len
        if current_chunk:
            chunks.append(current_chunk)
    else:
        # キーの関連性を考慮してクラスタリング(ソート)
        from . import lang_sorter
        key_clusters = lang_sorter.get_clustered_missing_keys({}, list(data_map.keys()))
        
        current_chunk = {}
        current_chars = 0
        for cluster_keys in key_clusters:
            for k in cluster_keys:
                v = data_map[k]
                v_len = len(str(v))
                if (len(current_chunk) >= BATCH_SIZE) or (current_chunk and current_chars + v_len > MAX_BATCH_CHARS):
                    chunks.append(current_chunk)
                    current_chunk = {}
                    current_chars = 0
                current_chunk[k] = v
                current_chars += v_len
        if current_chunk:
            chunks.append(current_chunk)
            
    return chunks

def process_single_file(client, src_path_full, tgt_path_full, target_dir, source_lang, target_lang, glossary, translation_memory=None, no_sort=False, handler=None, custom_system_instruction=None):
    """
    単一ファイルの翻訳ライフサイクルを管理する
    (読み込み -> 翻訳済みチェック -> メモリ適用 -> API翻訳 -> 保存)
    """
    global CANCEL_REQUESTED
    interrupted = False
    new_translations = {}
    existing_tgt_data = {}
    
    # 相対パスでの表示用
    try:
        rel_path = os.path.relpath(src_path_full, target_dir)
    except ValueError:
        rel_path = src_path_full
    print(f"\n[{rel_path}]")

    try:
        # ソースデータの読み込み
        source_data = handler.read(src_path_full) if handler else {}
        if not source_data:
            return False

        # 既存のターゲットファイルがあれば読み込んで差分を特定する
        if os.path.exists(tgt_path_full):
            try:
                loaded_data = handler.read(tgt_path_full)
                if isinstance(loaded_data, dict):
                    existing_tgt_data = loaded_data
            except Exception:
                pass

        # 翻訳が必要な(未翻訳の)キーのみを抽出
        missing_data = {k: v for k, v in source_data.items() if k not in existing_tgt_data}
        if not missing_data:
            return False
        
        # 1. 翻訳メモリ(TM)の適用
        tm_hit_count = 0
        final_missing_data = {}

        if translation_memory:
            for key, src_text in missing_data.items():
                if src_text in translation_memory:
                    new_translations[key] = translation_memory[src_text]
                    tm_hit_count += 1
                else:
                    final_missing_data[key] = src_text
        else:
            final_missing_data = missing_data

        if tm_hit_count > 0:
            print(f"  -> 翻訳メモリ適用: {tm_hit_count}件")
        
        # 2. API翻訳の実行
        if final_missing_data:
            print(f"  -> API翻訳対象: {len(final_missing_data)}件")
            
            chunks = create_chunks(final_missing_data, no_sort, src_path_full)
            if chunks:
                print(f"  -> 翻訳開始: {len(chunks)}バッチ")

            for i, chunk in enumerate(chunks, 1):
                # 中断要求の確認
                if CANCEL_REQUESTED:
                    print("\n  [!] 停止要求を検知。現在のバッチまでを保存して終了します...")
                    interrupted = True
                    break
                
                translated_chunk = translate_chunk(client, chunk, i, len(chunks), source_lang, target_lang, glossary, custom_system_instruction)
                if translated_chunk and isinstance(translated_chunk, dict):
                    new_translations.update(translated_chunk)
                else:
                    print(f"    [警告] Batch {i} 失敗 (スキップ)")
                
                # APIのレートリミットを考慮してわずかに待機
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n  [!] 中断を検知しました。現在のバッチまでを保存して終了します...")
        interrupted = True
    except Exception as e:
        print(f"  [エラー] {e}")
        return False
        
    # 翻訳結果の保存
    if new_translations:
        existing_tgt_data.update(new_translations)
        temp_file = f"{tgt_path_full}.tmp"
        try:
            if handler:
                handler.write(temp_file, existing_tgt_data)
            else:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(existing_tgt_data, f, ensure_ascii=False, indent=4)
            
            # 安全なアトミック書き換え
            os.replace(temp_file, tgt_path_full)
            
            suffix = " (中断による途中分)" if interrupted else ""
            print(f"  -> 保存完了: +{len(new_translations)}件{suffix}")
        except Exception as save_err:
            print(f"  [エラー] 保存失敗: {save_err}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    else:
        if not interrupted:
            print("  -> 追加の翻訳は不要です")

    return interrupted