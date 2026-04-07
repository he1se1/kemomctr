import os
import sys
import tempfile
from kemomctr.format_handlers import SnbtFormatHandler
import ftb_snbt_lib as slib

def test_snbt_list_handling():
    # 1. 準備: リスト形式を含むSNBTファイルを作成
    src_snbt = """{
    quest.01.desc: [
        "First line"
        ""
        "Third line"
    ]
    quest.01.title: "Simple Title"
}"""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "en_us.snbt")
        tgt_path = os.path.join(tmpdir, "ja_jp.snbt")
        
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(src_snbt)
            
        print("--- 読み込みテスト ---")
        data = SnbtFormatHandler.read(src_path)
        print(f"Read data: {data}")
        
        # 期待値チェック: 
        # quest.01.desc はユーザーの変更により '"First line"\n""\n"Third line"' になっているはず
        desc_val = data.get("quest.01.desc")
        expected_desc = '"First line"\n""\n"Third line"'
        if desc_val == expected_desc:
            print("SUCCESS: List read and joined with quotes correctly.")
        else:
            print(f"FAILURE: Expected {repr(expected_desc)}, got {repr(desc_val)}")
            
        print("\n--- 書き出しテスト ---")
        # 翻訳後のデータをシミュレート (引用符が維持されている想定)
        translated_data = {
            "quest.01.desc": '"最初の行"\n""\n"3行目"',
            "quest.01.title": '"日本語タイトル"' # 単一文字列も引用符付きで来る可能性を考慮
        }
        
        SnbtFormatHandler.write(tgt_path, translated_data)
        
        # 結果の検証
        with open(tgt_path, "r", encoding="utf-8") as f:
            written_snbt = f.read()
        print(f"Written SNBT content:\n{written_snbt}")
        
        # slibでロードして型を確認
        with open(tgt_path, "r", encoding="utf-8") as f:
            loaded = slib.load(f)
            
        desc_tag = loaded.get("quest.01.desc")
        if isinstance(desc_tag, slib.List):
            print("SUCCESS: quest.01.desc is a slib.List.")
            items = [str(i) for i in desc_tag]
            print(f"Items in list: {items}")
            if items == ["最初の行", "", "3行目"]:
                print("SUCCESS: Items are correctly stripped of quotes and preserved.")
            else:
                print(f"FAILURE: Items mismatch: {items}")
        else:
            print(f"FAILURE: quest.01.desc is not a List. Type: {type(desc_tag)}")
            
        title_tag = loaded.get("quest.01.title")
        if isinstance(title_tag, slib.String) and str(title_tag) == "日本語タイトル":
            print("SUCCESS: Single string quote stripped correctly.")
        else:
            print(f"FAILURE: Title tag mismatch or still has quotes: {repr(str(title_tag))}")

if __name__ == "__main__":
    try:
        test_snbt_list_handling()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
