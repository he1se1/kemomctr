import os
import json
import time
from google.genai import types

# ==========================================
# 設定
# ==========================================
MODEL_NAME = os.getenv("KEMOMCTR_MODEL", "gemini-3-flash-preview")
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

def translate_chunk(client, chunk_data, chunk_index, total_chunks, source_lang, target_lang, glossary):
    s_name = get_lang_name(source_lang)
    t_name = get_lang_name(target_lang)

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
    4. Context: Minecraft Gaming.
    
    # Glossary
    {json.dumps(glossary, ensure_ascii=False)}
    """

    prompt_text = f"""
    Translate these entries:
    {json.dumps(chunk_data, ensure_ascii=False)}
    """

    try:
        print(f"    - Batch {chunk_index}/{total_chunks} (約{len(chunk_data)}行) 処理中...", end="", flush=True)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1
            )
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

def process_single_file(client, src_path_full, tgt_path_full, target_dir, source_lang, target_lang, glossary):
    interrupted = False
    new_translations = {}
    existing_tgt_data = {}
    
    try:
        rel_path = os.path.relpath(src_path_full, target_dir)
    except ValueError:
        rel_path = src_path_full
    print(f"\n[{rel_path}]")

    try:
        # 1. 翻訳元の読み込み
        with open(src_path_full, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        if not isinstance(source_data, dict):
            return False

        # 2. 翻訳先の読み込みと修復
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

        # 3. 差分抽出
        missing_data = {k: v for k, v in source_data.items() if k not in existing_tgt_data}
        if not missing_data:
            return False
        
        print(f"  -> 未翻訳: {len(missing_data)}件")
        
        # 4. バッチ分割と翻訳
        items = list(missing_data.items())
        chunks = [dict(items[i:i + BATCH_SIZE]) for i in range(0, len(items), BATCH_SIZE)]
        
        if chunks:
            print(f"  -> 翻訳開始: {len(items)}項目 / {len(chunks)}バッチ")

        for i, chunk in enumerate(chunks, 1):
            translated_chunk = translate_chunk(client, chunk, i, len(chunks), source_lang, target_lang, glossary)
            if translated_chunk and isinstance(translated_chunk, dict):
                new_translations.update(translated_chunk)
            else:
                print(f"    [警告] Batch {i} 失敗 (スキップ)")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n  [!] ユーザーによる中断を検知しました。現在完了しているバッチまでのデータを保存して終了します...")
        interrupted = True
    except Exception as e:
        print(f"  [エラー] {e}")
        return False
        
    if new_translations:
        existing_tgt_data.update(new_translations)
        temp_file = f"{tgt_path_full}.tmp"
        try:
            # アトミック保存 (一時ファイルに書いてからリネーム)
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