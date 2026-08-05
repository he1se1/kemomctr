import os
import json
import time
from google.genai import types

# --- 追加: GUIからの中断を検知・スレッドを追跡するためのグローバル変数 ---
CANCEL_REQUESTED = False
current_thread = None
# -------------------------------------------------------------

# 設定
MODEL_NAME = os.getenv("KEMOMCTR_MODEL", "gemini-3.5-flash-lite")
BATCH_SIZE = 30

LANG_NAME_MAP = {
    "en_us": "English", "ja_jp": "Japanese",
    "zh_cn": "Chinese (Simplified)", "zh_tw": "Chinese (Traditional)",
    "ko_kr": "Korean", "ru_ru": "Russian",
    "fr_fr": "French", "de_de": "German", "es_es": "Spanish"
}

def get_lang_name(code):
    return LANG_NAME_MAP.get(code.lower(), code)

def normalize_response(result):
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

def translate_chunk(client, chunk_data, chunk_index, total_chunks, source_lang, target_lang, glossary, flex=False):
    s_name = get_lang_name(source_lang)
    t_name = get_lang_name(target_lang)

    # 用語集のフィルタリング（チャンク内のテキストに含まれる用語のみを抽出）
    filtered_glossary = {}
    if glossary:
        chunk_text_lower = " ".join(str(v) for v in chunk_data.values()).lower()
        for term, translation in glossary.items():
            if term.lower() in chunk_text_lower:
                filtered_glossary[term] = translation

    if filtered_glossary:
        print(f" (用語集ヒット: {len(filtered_glossary)}件)")

    system_instruction = f"""
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
    
    # Glossary
    {json.dumps(filtered_glossary, ensure_ascii=False)}
    """

    prompt_text = f"""
    Translate these entries:
    {json.dumps(chunk_data, ensure_ascii=False)}
    """

    try:
        print(f"    - Batch {chunk_index}/{total_chunks} (約{len(chunk_data)}行) 処理中...", end="", flush=True)
        config_kwargs = {
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
        if flex:
            config_kwargs["service_tier"] = "flex"

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt_text,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        raw_result = json.loads(response.text)
        final_dict = normalize_response(raw_result)

        if not final_dict:
            print(" [エラー: データ抽出失敗]")
            return None
        
        print(" OK")
        return final_dict
    except Exception as e:
        print(f" 失敗: {e}")
        return None

def process_single_file(client, src_path_full, tgt_path_full, target_dir, source_lang, target_lang, glossary, translation_memory=None, no_sort=False, flex=False):
    global CANCEL_REQUESTED
    interrupted = False
    new_translations = {}
    existing_tgt_data = {}
    
    try:
        rel_path = os.path.relpath(src_path_full, target_dir)
    except ValueError:
        rel_path = src_path_full
    print(f"\n[{rel_path}]")

    try:
        with open(src_path_full, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        if not isinstance(source_data, dict):
            return False

        if os.path.exists(tgt_path_full):
            try:
                with open(tgt_path_full, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    print(f"  [修復] {os.path.basename(tgt_path_full)} がリスト形式でした。辞書形式にリセットします。")
                    existing_tgt_data = {} 
                elif isinstance(loaded_data, dict):
                    existing_tgt_data = loaded_data
            except Exception:
                pass

        missing_data = {k: v for k, v in source_data.items() if k not in existing_tgt_data}
        if not missing_data:
            return False
        
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
            print(f"  -> 翻訳メモリ適用: {tm_hit_count}件 (API節約!)")
        
        if not final_missing_data and not new_translations:
            return False
        
        if final_missing_data:
            print(f"  -> API翻訳へ: {len(final_missing_data)}件")
            
            path_lower = src_path_full.lower()
            is_quest_path = "quest" in path_lower
            skip_sort = no_sort or is_quest_path
            
            chunks = []
            
            if skip_sort:
                reason = "[--no-sort] 指定あり" if no_sort else "パスに 'quest' を検知"
                print(f"  -> {reason}: 事前ソートを尊重し、元の順序でバッチ処理します")
                items = list(final_missing_data.items())
                for i in range(0, len(items), BATCH_SIZE):
                    chunks.append(dict(items[i:i + BATCH_SIZE]))
            else:
                from . import lang_sorter
                key_clusters = lang_sorter.get_clustered_missing_keys(source_data, list(final_missing_data.keys()))
                
                current_chunk = {}
                for cluster_keys in key_clusters:
                    if len(cluster_keys) > BATCH_SIZE:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = {}
                        for i in range(0, len(cluster_keys), BATCH_SIZE):
                            sub_chunk = {k: final_missing_data[k] for k in cluster_keys[i:i + BATCH_SIZE]}
                            chunks.append(sub_chunk)
                        continue

                    if len(current_chunk) + len(cluster_keys) > BATCH_SIZE:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = {}
                    
                    for k in cluster_keys:
                        current_chunk[k] = final_missing_data[k]
                        
                if current_chunk:
                    chunks.append(current_chunk)
            
            if chunks:
                print(f"  -> 翻訳開始: {len(final_missing_data)}項目 / {len(chunks)}バッチ")

            for i, chunk in enumerate(chunks, 1):
                # ▼ 追加: ループ毎にGUIからの中断リクエストをチェック ▼
                if CANCEL_REQUESTED:
                    print("\n  [!] GUIからの停止リクエストを検知。現在完了しているバッチまでのデータを保存して終了します...")
                    interrupted = True
                    break
                
                translated_chunk = translate_chunk(client, chunk, i, len(chunks), source_lang, target_lang, glossary, flex=flex)
                if translated_chunk and isinstance(translated_chunk, dict):
                    new_translations.update(translated_chunk)
                else:
                    print(f"    [警告] Batch {i} 失敗 (スキップ)")
                time.sleep(1)

    except KeyboardInterrupt:
        # CLI用の中断検知
        print("\n  [!] ユーザーによる中断を検知しました。現在完了しているバッチまでのデータを保存して終了します...")
        interrupted = True
    except Exception as e:
        print(f"  [エラー] {e}")
        return False
        
    if new_translations:
        existing_tgt_data.update(new_translations)
        temp_file = f"{tgt_path_full}.tmp"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(existing_tgt_data, f, ensure_ascii=False, indent=4)
            os.replace(temp_file, tgt_path_full)
            
            count_text = f" (中断により途中まで)" if interrupted else ""
            print(f"  -> 保存完了: +{len(new_translations)}件{count_text}")
        except Exception as save_err:
            print(f"  [エラー] 保存に失敗しました: {save_err}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    else:
        if not interrupted:
            print("  -> 追加なし")

    return interrupted