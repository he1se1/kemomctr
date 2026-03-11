"""
kemomctr
Minecraft Mod 翻訳 & リソースパック生成 CLIツール
"""

import argparse
import sys

from . import recursive_translator
from . import pack_maker

def main():
    parser = argparse.ArgumentParser(
        prog="kemomctr", 
        description="Minecraft Modの言語ファイルを翻訳し、リソースパックとして統合するツール"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="実行するコマンドを選択してください")
    subparsers.required = True

    # コマンド 1: tr (translate)
    parser_tr = subparsers.add_parser("tr", help="指定ディレクトリのlangファイルを再帰的に翻訳します")
    parser_tr.add_argument("directory", help="対象のディレクトリパス")
    parser_tr.add_argument("-s", "--source", default="en_us", help="翻訳元の言語コード (デフォルト: en_us)")
    parser_tr.add_argument("-t", "--target", default="ja_jp", help="翻訳先の言語コード (デフォルト: ja_jp)")
    parser_tr.add_argument("-g", "--glossary", default=None, help="用語集CSVファイルのパス")
    parser_tr.add_argument("-r", "--ref", default=None, help="旧バージョンのディレクトリパス (翻訳を流用するために使用)")

    # コマンド 2: col (collect)
    parser_col = subparsers.add_parser("col", help="翻訳済みのファイルを集約してリソースパックを作成します")
    parser_col.add_argument("source", help="検索元のディレクトリパス")
    parser_col.add_argument("dest", help="保存先（リソースパック）のディレクトリパス")
    parser_col.add_argument("--en", action="store_true", help="en_us.json も一緒に収集・マージする場合は指定")
    parser_col.add_argument(
        "-m", "--mc-version", 
        default="1.20.1", 
        help="対象のMinecraftバージョン(デフォルト: 1.20.1)"
    )

    args = parser.parse_args()

    # コマンドルーティング
    if args.command == "tr":
        recursive_translator.run_recursive(args.directory, args.source, args.target, args.glossary, args.ref)
    elif args.command == "col":
        pack_maker.run_pack_maker(args.source, args.dest, args.en, args.mc_version)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] 処理が中断されました。")
        sys.exit(0)