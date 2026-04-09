"""
kemomctr コマンドラインインターフェース
Minecraft Modの翻訳支援とリソースパック作成を統合するエントリポイント
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
    """引数を解析し、適切なコマンドまたはGUIを実行する"""
    if len(sys.argv) <= 1:
        # 引数がない場合はGUIモードで起動
        gui.run_gui()
        return

    parser = argparse.ArgumentParser(
        prog="kemomctr", 
        description="Minecraft Modの言語ファイルを翻訳し、リソースパックとして統合するツール"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="実行するコマンドを選択してください")
    subparsers.required = True

    # 翻訳コマンド (tr)
    parser_tr = subparsers.add_parser("tr", help="指定ディレクトリのファイルを再帰的にAPI翻訳します")
    parser_tr.add_argument("directory", help="対象のディレクトリパス")
    parser_tr.add_argument("-s", "--source", default="en_us", help="翻訳元の言語コード (デフォルト: en_us)")
    parser_tr.add_argument("-t", "--target", default="ja_jp", help="翻訳先の言語コード (デフォルト: ja_jp)")
    parser_tr.add_argument("-f", "--format", dest="format_id", default="json", help="フォーマット(json, lang, snbt)")
    parser_tr.add_argument("-g", "--glossary", default=None, help="用語集CSVのパス")
    parser_tr.add_argument("-r", "--ref", default=None, help="旧バージョンのディレクトリ(翻訳メモリとして使用)")
    parser_tr.add_argument("-p", "--prompt", default=None, help="カスタムシステムプロンプトのパス")
    parser_tr.add_argument("--no-sort", action="store_true", help="キーの自動ソートを無効化")

    # 集約コマンド (col)
    parser_col = subparsers.add_parser("col", help="翻訳済みファイルを収集しリソースパックを作成します")
    parser_col.add_argument("source", help="検索元のディレクトリパス")
    parser_col.add_argument("dest", help="保存先のディレクトリパス")
    parser_col.add_argument("-f", "--format", dest="format_id", default="json", help="対象フォーマット")
    parser_col.add_argument("--en", action="store_true", help="en_usも収集対象に含める")
    parser_col.add_argument("-m", "--mc-version", default="1.20.1", help="対象のMinecraftバージョン")

    # 用語集作成コマンド (glos)
    parser_glos = subparsers.add_parser("glos", help="ソースから名詞句を抽出し用語集を作成します")
    parser_glos.add_argument("src_dir", help="探索元のソースディレクトリパス")
    parser_glos.add_argument("--tgt-dir", default=None, help="訳語を抽出するディレクトリパス")
    parser_glos.add_argument("-o", "--output", default="glossary_generated.csv", help="出力CSVのパス")
    parser_glos.add_argument("-s", "--source", default="en_us", help="翻訳元の言語コード")
    parser_glos.add_argument("-t", "--target", default="ja_jp", help="翻訳先の言語コード")
    parser_glos.add_argument("-f", "--format", dest="format_id", default="json", help="対象フォーマット")

    args = parser.parse_args()

    # コマンドに応じた処理の振り分け
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
    """メインエントリポイント。例外処理と終了待ちを管理する"""
    try:
        run_app()
    except KeyboardInterrupt:
        # GUIスレッドが動作中の場合は終了を待機
        if single_translator.current_thread and single_translator.current_thread.is_alive():
            print("\n\n[!] 中断要求を受け付けました。データの安全な保存を待機しています...")
            single_translator.CANCEL_REQUESTED = True
            single_translator.current_thread.join(timeout=60.0)
            print("[!] 終了しました。")
        else:
            # CLI実行時は個別の処理内で中断がハンドルされるため、メッセージなしで終了可能
            pass

if __name__ == "__main__":
    main()