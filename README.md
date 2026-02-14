# kemomctr
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

AI-driven Minecraft Mod translator featuring recursive search, glossary support, and resume functionality via Gemini 3.0 Flash. Supports MC1.13-1.20.  
MinecraftのModのAI翻訳ツール。翻訳対象ファイルを探索しての翻訳が可能。Gemini 3.0 Flashを使用。Minecraft バージョン1.13から1.20までに対応。

# 📥 セットアップ

このツールは、Python環境を汚さずにCLIツールを導入できる `pipx` でのインストールを推奨しています。

## 1. ツールのインストール
以下のコマンドでGitHubから直接インストールできます。

```bash
pipx install git+https://github.com/he1se1/kemomctr.git
```

## 2. APIキーの設定
翻訳にはGoogle GeminiのAPIキーが必要です。環境変数 GOOGLE_API_KEY に取得したAPIキーを設定してください。

<details>
<summary>環境変数の設定のしかた</summary>

Windows (PowerShell):

```powershell
$env:GOOGLE_API_KEY="<YOUR_API_KEY>"
```

永続化させたい場合は、Windowsの「システムの詳細設定」＞「環境変数」から追加してください。

Mac / Linux:

```bash
export GOOGLE_API_KEY="<YOUR_API_KEY>"
```

永続化させたい場合はこれを `~/.bashrc` や `~/.zshrc` に追記してください。

</details>

# 📄 使用方法
kemomctr は、翻訳を行う `tr` コマンドと、リソースパックを構築する `col` コマンドの2つの機能を持っています。

## 1. `tr` 翻訳モード
指定したディレクトリ以下にある言語ファイルを探索し、Geminiで翻訳し同じ場所に結果を保存します。

基本コマンド
```Bash
kemomctr tr /modpack/kubejs/assets/ -s en_us -t ja_jp -g path/to/glossary.csv
```
オプション(すべて任意)
- `-s` / `--source` : 翻訳元の言語コード (デフォルト: en_us)
- `-t` / `--target` : 翻訳先の言語コード (デフォルト: ja_jp)
- `-g` / `--glossary` : 用語集のパス

CSV形式の用語集を与えて訳語を指定することができます。  
1行目に言語コードを記述し、それ以下に訳語の組を記述します。実行時はソースとターゲットに指定した言語のカラムのみが使われます。また各行について、どちらかの値が空欄ならそれは無視されます。  
glossary.csvの記述例
```
en_us,zh_cn,ja_jp
Certus Quartz,赛特斯石英,ケルタスクォーツ
...
```

動作はCTRL+C(KeyboardInterrupt)で中断できます。中断した場合はそれまでの進捗が保存されます。

種々の原因で、翻訳は偶にバッチ単位で失敗することがあります。失敗したとき、そのバッチは無視して言語ファイルが生成されます。
次回実行時、未翻訳のキーを自動的に検出して翻訳します。

## 2. `col` リソースパック構築モード
指定したディレクトリの中を探索し、`ja_jp.json`があればそれを`assets/`以下のディレクトリ構造を保って保存先にコピーします。  
UTI mod用などに、`en_us.json`も同様にコピーするオプションがあります。

基本コマンド
```Bash
kemomctr cor /some/dir/contains/lang/files/ /direcory/to/save/resourcepack/ -m 1.18.2 --en
```

オプション
- `-m` / `--mc-version` : Minecraftのバージョン (デフォルト: 1.20.1)  
`pack_format`の値を直接与えることもできます
- `--en` : このオプションをつけると、`en_us.json`もコピーします。


# 🗺️実装予定機能
- 既存の翻訳からのglossaryの自動生成および動的生成
- アップデートに対応するための差分翻訳(ソース言語の差分を確認して再度翻訳)
- coremod等のjarを展開し翻訳する
- MC1.21以降のsnbt形式のlangファイルへの対応

プルリクエストやIssuesでの要望も歓迎しています。