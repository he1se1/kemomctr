"""
kemomctr MCP Server
Minecraft Mod Localization MCP Server implementation using FastMCP
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from mcp.server.mcpserver import MCPServer, Context

from . import single_translator
from . import recursive_translator
from . import tm_manager
from . import pack_maker
from . import glossary_maker

# Initialize MCPServer
mcp = MCPServer("kemomctr", instructions="Minecraft Mod Localization Assistant MCP Server")


@mcp.tool()
def scan_untranslated_batches(
    target_dir: str,
    source_lang: str = "en_us",
    target_lang: str = "ja_jp",
    glossary_path: Optional[str] = None,
    ref_dir: Optional[str] = None,
    no_sort: bool = False
) -> Dict[str, Any]:
    """
    指定したディレクトリ配下のMinecraft Mod言語ファイルを探索し、
    未翻訳キーのバッチ（システムプロンプト、ヒット用語集、TM適用結果を含む）を取得します。
    """
    target_path = Path(target_dir)
    if not target_path.exists():
        return {"error": f"パスが見つかりません: {target_dir}"}

    source_filename = f"{source_lang}.json"
    target_filename = f"{target_lang}.json"

    glossary = recursive_translator.load_glossary(glossary_path, source_lang, target_lang) if glossary_path else {}
    translation_memory = tm_manager.build_translation_memory(ref_dir, source_lang, target_lang) if ref_dir else {}

    file_results = []

    def process_file(src_full, tgt_full):
        try:
            prepared = single_translator.prepare_translation_batches(
                src_path_full=src_full,
                tgt_path_full=tgt_full,
                source_lang=source_lang,
                target_lang=target_lang,
                glossary=glossary,
                translation_memory=translation_memory,
                no_sort=no_sort
            )
            if prepared:
                # TM適用結果があれば即座に保存
                if prepared["tm_applied_translations"]:
                    single_translator.save_translation_results(
                        tgt_full,
                        prepared["existing_tgt_data"],
                        prepared["tm_applied_translations"]
                    )
                file_results.append({
                    "src_path_full": prepared["src_path_full"],
                    "tgt_path_full": prepared["tgt_path_full"],
                    "tm_hit_count": prepared["tm_hit_count"],
                    "total_missing_count": prepared["total_missing_count"],
                    "api_missing_count": prepared["api_missing_count"],
                    "chunks": prepared["chunks"]
                })
        except Exception as e:
            file_results.append({"src_path_full": src_full, "error": str(e)})

    if target_path.is_file():
        if target_path.name == source_filename:
            src_full = str(target_path)
            tgt_full = str(target_path.parent / target_filename)
            process_file(src_full, tgt_full)
    else:
        for root, _, files in os.walk(target_path):
            if source_filename in files:
                src_full = os.path.join(root, source_filename)
                tgt_full = os.path.join(root, target_filename)
                process_file(src_full, tgt_full)

    return {
        "target_dir": target_dir,
        "files_count": len(file_results),
        "files": file_results
    }


@mcp.tool()
def save_translation_batch(
    tgt_path_full: str,
    new_translations: Dict[str, str],
    existing_tgt_data: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    翻訳済みキー・値の辞書を指定のターゲット言語ファイル（例: ja_jp.json）に保存・追加します。
    """
    if existing_tgt_data is None:
        existing_tgt_data = {}
        if os.path.exists(tgt_path_full):
            try:
                with open(tgt_path_full, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        existing_tgt_data = loaded
            except Exception:
                pass

    success = single_translator.save_translation_results(
        tgt_path_full=tgt_path_full,
        existing_tgt_data=existing_tgt_data,
        new_translations=new_translations
    )

    if success:
        return {
            "status": "success",
            "tgt_path_full": tgt_path_full,
            "saved_count": len(new_translations)
        }
    else:
        return {
            "status": "error",
            "tgt_path_full": tgt_path_full,
            "message": "ファイルの保存に失敗しました。"
        }


@mcp.tool()
def build_resource_pack(
    source_dir: str,
    dest_dir: str,
    include_en: bool = False,
    mc_version: str = "1.20.1"
) -> Dict[str, Any]:
    """
    翻訳済みlangファイルを集約し、Minecraft用リソースパックを構築します。
    """
    try:
        pack_maker.run_pack_maker(
            src_dir=source_dir,
            dest_dir=dest_dir,
            include_en=include_en,
            mc_version=mc_version
        )
        return {
            "status": "success",
            "source_dir": source_dir,
            "dest_dir": dest_dir,
            "mc_version": mc_version
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def extract_glossary_terms(
    src_dir: str,
    output_csv: str = "glossary_generated.csv",
    tgt_dir: Optional[str] = None,
    source_lang: str = "en_us",
    target_lang: str = "ja_jp"
) -> Dict[str, Any]:
    """
    指定ディレクトリから名詞キーを抽出して用語集CSVを自動生成・更新します。
    """
    try:
        glossary_maker.run_glossary_maker(
            src_dir=src_dir,
            tgt_dir=tgt_dir,
            output_csv=output_csv,
            source_lang=source_lang,
            target_lang=target_lang
        )
        return {
            "status": "success",
            "output_csv": output_csv
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def run_mcp_server():
    """
    MCP サーバーを stdio トランスポートで起動します。
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_mcp_server()
