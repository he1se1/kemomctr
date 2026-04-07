import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseFormatHandler(ABC):
    format_id: str = ""

    @classmethod
    @abstractmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        """このフォーマットのソースファイルとして妥当か判定する (例: en_us.json かどうか)"""
        pass

    @classmethod
    @abstractmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        """ターゲットのファイル名を生成する (例: en_us.json -> ja_jp.json)"""
        pass

    @classmethod
    @abstractmethod
    def read(cls, filepath: str) -> Dict[str, str]:
        """ファイルを読み込み、Key-Value 辞書を返す。失敗時や非対応構造の場合は ValueError などを発生させるか空辞書を返す。"""
        pass

    @classmethod
    @abstractmethod
    def write(cls, filepath: str, data: Dict[str, str]):
        """辞書データを元のフォーマット形式に従って書き出す"""
        pass

class JsonFormatHandler(BaseFormatHandler):
    format_id = "json"

    @classmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        return filename == f"{source_lang}.json"

    @classmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        # JSONの場合は常に {target_lang}.json とする
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
                        # 文字列のリストなら1つずつ""で囲み、改行で結合
                        lines = [f'\"{item}\"' for item in v]
                        data[k] = "\n".join(lines)
                    else:
                        # 単体のタグ（String, Intなど）は文字列化
                        data[k] = str(v)
            return data
        except Exception as e:
            print(f"  [SnbtFormatHandler] Read Error: {e}")
            return {}

    @classmethod
    def write(cls, filepath: str, data: Dict[str, str]):
        import ftb_snbt_lib as slib
        
        # 既存内容があれば型合わせを試みる
        snbt_data = slib.Compound({})
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    snbt_data = slib.load(f)
            except Exception:
                pass

        for k, v in data.items():
            if "\n" in v:
                # 改行が含まれる場合は SNBT のリスト ([]) として保存
                lines = v.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    # 前後の引用符を最大1つずつ剥ぎ取る (read時に付加された可能性があるため)
                    if len(line) >= 2 and line.startswith('"') and line.endswith('"'):
                        line = line[1:-1]
                    cleaned_lines.append(line)
                snbt_data[k] = slib.List([slib.String(l) for l in cleaned_lines])
            else:
                # 単一文字列。こちらも念のため前後の引用符を剥ぎ取る
                val = v.strip()
                if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                snbt_data[k] = slib.String(val)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # FTB SNBT 形式 (改行区切り) で書き出し
            slib.dump(snbt_data, f, comma_sep=False)

class LangFormatHandler(BaseFormatHandler):
    format_id = "lang"

    @classmethod
    def is_source_file(cls, filename: str, source_lang: str) -> bool:
        # 古いバージョンでは en_US.lang のような大文字小文字が混在することがあるが、
        # 引数 source_lang (例: en_us) に合わせて柔軟に判定する。
        return filename.lower() == f"{source_lang.lower()}.lang"

    @classmethod
    def get_target_filename(cls, filename: str, target_lang: str) -> str:
        # 一般にlangフォーマットでは国コード部分を大文字にする (ja_JP.lang)
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

# 使用可能な全ハンドラーのリスト
_HANDLERS = [
    JsonFormatHandler,
    SnbtFormatHandler,
    LangFormatHandler,
]

def get_handler_by_id(format_id: str) -> Optional[BaseFormatHandler]:
    """指定されたフォーマットIDに合致するハンドラーを探して返す"""
    for handler in _HANDLERS:
        if getattr(handler, "format_id", "") == format_id.lower():
            return handler
    return None

def get_supported_formats() -> list[str]:
    return [h.format_id for h in _HANDLERS]
