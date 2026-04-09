"""
フォーマットハンドラ・モジュール
JSON, SNBT, .lang 各形式の読み書きと判定を抽象化する
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, List

class BaseFormatHandler(ABC):
    """
    全てのフォーマットハンドラの基底クラス。
    新しいフォーマットを追加する場合は、このクラスを継承する。
    """
    format_id: str = ""

    @classmethod
    @abstractmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        """
        ファイル名が指定された言語のソースファイルであるか判定する
        例: en_us.json かどうか
        """
        pass

    @classmethod
    @abstractmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        """
        翻訳先のファイル名を生成する
        例: en_us.json -> ja_jp.json
        """
        pass

    @classmethod
    @abstractmethod
    def read(cls, filepath: str) -> Dict[str, str]:
        """
        ファイルを読み込み、Key-Value形式の辞書を返す。
        失敗した場合は空の辞書を返す。
        """
        pass

    @classmethod
    @abstractmethod
    def write(cls, filepath: str, data: Dict[str, str]):
        """
        辞書データを対応するフォーマットで書き出す。
        """
        pass

class JsonFormatHandler(BaseFormatHandler):
    """標準的なJSON形式のMod言語ファイルを扱う"""
    format_id = "json"

    @classmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        return filename == f"{source_lang}.json"

    @classmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        return f"{target_lang}.json"

    @classmethod
    def read(cls, filepath: str) -> Dict[str, str]:
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    @classmethod
    def write(cls, filepath: str, data: Dict[str, str]):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

class SnbtFormatHandler(BaseFormatHandler):
    """FTB Quest等で使用されるSNBT形式のファイルを扱う"""
    format_id = "snbt"

    @classmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        return filename == f"{source_lang}.snbt"

    @classmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        return f"{target_lang}.snbt"

    @classmethod
    def read(cls, filepath: str) -> Dict[str, str]:
        if not os.path.exists(filepath):
            return {}
        try:
            import ftb_snbt_lib as slib
            with open(filepath, 'r', encoding='utf-8') as f:
                snbt_data = slib.load(f)
            
            data = {}
            if isinstance(snbt_data, slib.Compound):
                for k, v in snbt_data.items():
                    if isinstance(v, slib.List):
                        # SNBTのリスト(改行区切り)を読み込み
                        lines = [f'\"{item}\"' for item in v]
                        data[k] = "\n".join(lines)
                    else:
                        data[k] = str(v)
            return data
        except Exception as e:
            print(f"  [SnbtFormatHandler] 読み込みエラー: {e}")
            return {}

    @classmethod
    def write(cls, filepath: str, data: Dict[str, str]):
        import ftb_snbt_lib as slib
        
        # 既存ファイルのメタデータを保持するため、一度読み込みを試みる
        snbt_data = slib.Compound({})
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    snbt_data = slib.load(f)
            except Exception:
                pass

        for k, v in data.items():
            if "\n" in v:
                # 改行が含まれる場合は SNBT のリスト形式 ([]) に変換
                lines = v.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    # 読み込み時に付加した可能性のある引用符を除去
                    if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
                        line = line[1:-1]
                    cleaned_lines.append(line)
                snbt_data[k] = slib.List([slib.String(l) for l in cleaned_lines])
            else:
                # 単一の文字列値
                val = v.strip()
                if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                snbt_data[k] = slib.String(val)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # FTB SNBT 形式(カンマなし・改行あり)で出力
            slib.dump(snbt_data, f, comma_sep=False)

class LangFormatHandler(BaseFormatHandler):
    """Minecraft 舊バージョンの .lang 形式(key=value)を扱う"""
    format_id = "lang"

    @classmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        # 大文字小文字の差異を許容する (en_us.lang vs en_US.lang)
        return filename.lower() == f"{source_lang.lower()}.lang"

    @classmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        # .lang形式では慣習的に国コードを大文字にする
        parts = target_lang.split('_')
        if len(parts) == 2:
            return f"{parts[0]}_{parts[1].upper()}.lang"
        return f"{target_lang}.lang"

    @classmethod
    def read(cls, filepath: str) -> Dict[str, str]:
        if not os.path.exists(filepath):
            return {}
        data = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 空行やコメント行をスキップ
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        data[k.strip()] = v.strip()
        except Exception:
            pass
        return data

    @classmethod
    def write(cls, filepath: str, data: Dict[str, str]):
        with open(filepath, 'w', encoding='utf-8') as f:
            for k, v in data.items():
                f.write(f"{k}={v}\n")

# 定義済みの全ハンドラのリスト
_HANDLERS = [
    JsonFormatHandler,
    SnbtFormatHandler,
    LangFormatHandler,
]

def get_handler_by_id(format_id: str) -> Optional[BaseFormatHandler]:
    """フォーマットIDに対応するハンドラー実体を返す"""
    for handler in _HANDLERS:
        if getattr(handler, "format_id", "") == format_id.lower():
            return handler
    return None

def get_supported_formats() -> List[str]:
    """サポートされている全フォーマットIDのリストを返す"""
    return [h.format_id for h in _HANDLERS]
