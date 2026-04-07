"""
kemomctr
Minecraft Mod 翻訳 & リソースパック生成 CLIツール
"""

import argparse
import sys
import os

from . import gui
from . import recursive_translator
from . import pack_maker
from . import single_translator
from . import glossary_maker

def run_app():
    if len(sys.argv) == 1:
        gui.run_gui()
        return

    parser = argparse.ArgumentParser(
        prog="kemomctr", 
        description="Minecraft Modの言語ファイルを翻訳し、リソースパックとして統合するツール"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="実行するコマンドを選択してください")
    subparsers.required = True

    parser_tr = subparsers.add_parser("tr", help="指定ディレクトリのlangファイルを再帰的に翻訳します")
    parser_tr.add_argument("directory", help="対象のディレクトリパス")
    parser_tr.add_argument("-s", "--source", default="en_us", help="翻訳元の言語コード (デフォルト: en_us)")
    parser_tr.add_argument("-t", "--target", default="ja_jp", help="翻訳先の言語コード (デフォルト: ja_jp)")
    parser_tr.add_argument("-f", "--format", dest="format_id", default="json", help="対象フォーマット(json, lang, snbt) (デフォルト: json)")
    parser_tr.add_argument("-g", "--glossary", default=None, help="用語集CSVファイルのパス")
    parser_tr.add_argument("-r", "--ref", default=None, help="旧バージョンのディレクトリパス (翻訳を流用するために使用)")
    parser_tr.add_argument("-p", "--prompt", default=None, help="カスタムシステムプロンプトファイルのパス")
    parser_tr.add_argument("--no-sort", action="store_true", help="キーの自動ソートを無効化し、元の順序でバッチ処理します")

    parser_col = subparsers.add_parser("col", help="翻訳済みのファイルを集約してリソースパックを作成します")
    parser_col.add_argument("source", help="検索元のディレクトリパス")
    parser_col.add_argument("dest", help="保存先（リソースパック）のディレクトリパス")
    parser_col.add_argument("-f", "--format", dest="format_id", default="json", help="対象フォーマット(json, lang, snbt) (デフォルト: json)")
    parser_col.add_argument("--en", action="store_true", help="en_us.json も一緒に収集・マージする場合は指定")
    parser_col.add_argument("-m", "--mc-version", default="1.20.1", help="対象のMinecraftバージョン(デフォルト: 1.20.1)")

    parser_glos = subparsers.add_parser("glos", help="指定ディレクトリ以下を走査し、名詞句から用語集を作成します")
    parser_glos.add_argument("src_dir", help="探索元のソースディレクトリパス")
    parser_glos.add_argument("--tgt-dir", default=None, help="訳語を抽出するターゲットディレクトリパス（任意）")
    parser_glos.add_argument("-o", "--output", default="glossary_generated.csv", help="出力・追記するCSVのパス")
    parser_glos.add_argument("-s", "--source", default="en_us", help="翻訳元の言語コード (デフォルト: en_us)")
    parser_glos.add_argument("-t", "--target", default="ja_jp", help="翻訳先の言語コード (デフォルト: ja_jp)")
    parser_glos.add_argument("-f", "--format", dest="format_id", default="json", help="対象フォーマット(json, lang, snbt) (デフォルト: json)")

    args = parser.parse_args()

    if args.command == "tr":
        custom_prompt = None
        if args.prompt:
            if os.path.exists(args.prompt):
                with open(args.prompt, "r", encoding="utf-8") as f:
                    custom_prompt = f.read()
            else:
                print(f"[警告] プロンプトファイルが見つかりません: {args.prompt}")

        recursive_translator.run_recursive(
            args.directory, args.source, args.target, args.glossary, args.ref, args.no_sort, args.format_id, custom_prompt
        )
    elif args.command == "col":
        pack_maker.run_pack_maker(
            args.source, args.dest, args.en, args.mc_version, args.format_id
        )
    elif args.command == "glos":
        glossary_maker.run_glossary_maker(
            args.src_dir, args.tgt_dir, args.output, args.source, args.target, args.format_id
        )

def main():
    try:
        run_app()
    except KeyboardInterrupt:
        # 裏のスレッド(GUI)が動いている場合は停止リクエストを送信して待つ
        if single_translator.current_thread and single_translator.current_thread.is_alive():
            print("\n\n[!] 中断要求を受け付けました。安全に終了するため、データの保存を待機しています...")
            single_translator.CANCEL_REQUESTED = True
            single_translator.current_thread.join(timeout=60.0)
            print("[!] 終了します。")
        else:
            # CLI実行時は内側の各モジュールで KeyboardInterrupt が処理され、
            # 適切に保存された後にここへ到達するはずなので、そのまま終了する。
            pass

if __name__ == "__main__":
    main()