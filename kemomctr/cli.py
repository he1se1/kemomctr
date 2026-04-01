"""
kemomctr
Minecraft Mod 翻訳 & リソースパック生成 CLIツール
"""

import argparse
import sys

from . import gui
from . import gui
from . import recursive_translator
from . import pack_maker
from . import single_translator
from . import glossary_maker

def run_app():
    if len(sys.argv) == 1:
        gui.run_gui()
        return

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
    parser_tr.add_argument("-g", "--glossary", default=None, help="用語集CSVファイルのパス")
    parser_tr.add_argument("-r", "--ref", default=None, help="旧バージョンのディレクトリパス (翻訳を流用するために使用)")
    parser_tr.add_argument("--no-sort", action="store_true", help="キーの自動ソートを無効化し、元の順序でバッチ処理します")

    parser_col = subparsers.add_parser("col", help="翻訳済みのファイルを集約してリソースパックを作成します")
    parser_col.add_argument("source", help="検索元のディレクトリパス")
    parser_col.add_argument("dest", help="保存先（リソースパック）のディレクトリパス")
    parser_col.add_argument("--en", action="store_true", help="en_us.json も一緒に収集・マージする場合は指定")
    parser_col.add_argument("-m", "--mc-version", default="1.20.1", help="対象のMinecraftバージョン(デフォルト: 1.20.1)")

    parser_glos = subparsers.add_parser("glos", help="指定ディレクトリ以下を走査し、名詞句から用語集を作成します")
    parser_glos.add_argument("src_dir", help="探索元のソースディレクトリパス")
    parser_glos.add_argument("--tgt-dir", default=None, help="訳語を抽出するターゲットディレクトリパス（任意）")
    parser_glos.add_argument("-o", "--output", default="glossary_generated.csv", help="出力・追記するCSVのパス")
    parser_glos.add_argument("-s", "--source", default="en_us", help="翻訳元の言語コード (デフォルト: en_us)")
    parser_glos.add_argument("-t", "--target", default="ja_jp", help="翻訳先の言語コード (デフォルト: ja_jp)")

    args = parser.parse_args()

    if args.command == "tr":
        recursive_translator.run_recursive(
            args.directory, args.source, args.target, args.glossary, args.ref, args.no_sort
        )
        recursive_translator.run_recursive(
            args.directory, args.source, args.target, args.glossary, args.ref, args.no_sort
        )
    elif args.command == "col":
        pack_maker.run_pack_maker(
            args.source, args.dest, args.en, args.mc_version
        )
    elif args.command == "glos":
        glossary_maker.run_glossary_maker(
            args.src_dir, args.tgt_dir, args.output, args.source, args.target
        )

def main():
    try:
        run_app()
        run_app()
    except KeyboardInterrupt:
        print("\n\n[!] 中断要求を受け付けました。安全に終了するため、データの保存を待機しています...")
        
        # 裏のスレッドに停止リクエストを送信
        single_translator.CANCEL_REQUESTED = True
        
        # 翻訳スレッドが動いている場合は、キリの良いところで保存が終わるまで最大60秒待つ
        if single_translator.current_thread and single_translator.current_thread.is_alive():
            single_translator.current_thread.join(timeout=60.0)
            
        print("[!] 終了します。")
        print("\n\n[!] 中断要求を受け付けました。安全に終了するため、データの保存を待機しています...")
        
        # 裏のスレッドに停止リクエストを送信
        single_translator.CANCEL_REQUESTED = True
        
        # 翻訳スレッドが動いている場合は、キリの良いところで保存が終わるまで最大60秒待つ
        if single_translator.current_thread and single_translator.current_thread.is_alive():
            single_translator.current_thread.join(timeout=60.0)
            
        print("[!] 終了します。")
        sys.exit(0)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()