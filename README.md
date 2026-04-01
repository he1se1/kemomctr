# kemomctr
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)

AI-driven Minecraft Mod translator featuring recursive search, glossary support, and resume functionality via Gemini. Supports MC1.13-1.20.  
MinecraftのModのAI翻訳ツール。翻訳対象ファイルを探索しての翻訳が可能。Geminiを使用。Minecraft バージョン1.13から1.20までに対応。

# 📥 セットアップ

Python環境を汚さずにCLIツールを導入できる `uv`や`pipx` でのインストールを推奨しています。

## 1. ツールのインストール
以下のコマンドでGitHubから直接インストールできます。

```bash
uv tool install git+https://github.com/he1se1/kemomctr.git
```

```bash
pipx install git+https://github.com/he1se1/kemomctr.git
```

## 2. 環境変数の設定
翻訳にはGoogle GeminiのAPIキーが必要です。環境変数 `GOOGLE_API_KEY` に取得したAPIキーを設定してください。

環境変数`KEMOMCTR_MODEL`で使用するモデルを指定できます。デフォルト値は`gemini-3-flash-preview`です。

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
引数を何もつけずに実行すると、GUIが立ち上がります。

kemomctr は、翻訳を行う `tr` コマンド、リソースパックを構築する `col` コマンド、および用語集を自動生成する `glos` コマンドの3つの機能を持っています。

## 1. `tr` 翻訳モード
指定したディレクトリ以下にある言語ファイルを探索し、Geminiで翻訳し同じ場所に結果を保存します。

基本コマンド
```Bash
kemomctr tr /path/to/lang/files -s en_us -t ja_jp -g path/to/glossary.csv
```
オプション(すべて任意)
- `-s` / `--source` : 翻訳元の言語コード (デフォルト: en_us)
- `-t` / `--target` : 翻訳先の言語コード (デフォルト: ja_jp)
- `-g` / `--glossary` : 用語集のパス
- `-r` / `--ref` : 旧バージョンのパス
- `--no-sort` : このオプションを付けると、翻訳前にファイル内のキーの順番を変更しません。つけなくてもパスに`quest`を含むファイルはデフォルトで順番を変更しません。

CSV形式の用語集を与えて訳語を指定することができます。  
1行目に言語コードを記述し、それ以下に訳語の組を記述します。実行時はソースとターゲットに指定した言語のカラムのみが使われます。また各行について、どちらかの値が空欄ならそれは無視されます。  
glossary.csvの記述例
```
en_us,zh_cn,ja_jp
Certus Quartz,赛特斯石英,ケルタスクォーツ
...
```

Modpackの更新時などに、旧バージョンの翻訳があれば、それを流用することでAPIと時間を節約できます。オプション`-r`に与えたパス以下のディレクトリを探索し、同じディレクトリに翻訳元と先のlangファイルが両方存在すれば、それから辞書を生成し、翻訳時に流用します。性質上、完全一致でのみ翻訳を流用することができます。

動作はCTRL+C(KeyboardInterrupt)で中断できます。中断した場合はそれまでの進捗が保存されます。

種々の原因で、翻訳は偶にバッチ単位で失敗することがあります。失敗したとき、そのバッチは無視して言語ファイルが生成されます。
次回実行時、未翻訳のキーを自動的に検出して翻訳します。

## 2. `col` リソースパック構築モード
指定したディレクトリの中を探索し、`ja_jp.json`があればそれを`assets/`以下のディレクトリ構造を保って保存先にコピーします。  
UTI mod用などに、`en_us.json`も同様にコピーするオプションがあります。

基本コマンド
```Bash
kemomctr col /some/dir/contains/lang/files/ /direcory/to/save/resourcepack/ -m 1.18.2 --en
```

オプション
- `-m` / `--mc-version` : Minecraftのバージョン (デフォルト: 1.20.1)  
`pack_format`の値を直接与えることもできます
- `--en` : このオプションをつけると、`en_us.json`もコピーします。

## 3. `glos` 用語集自動生成モード
指定したディレクトリ以下を探索し、キー名に`item.`や`block.`などを含む名詞句を自動的に収集して、用語集（CSV形式）を作成します。既存のファイルが指定された場合は上書きせず**追記**します。GUIの「用語集生成 (glos)」タブからも実行可能です。

基本コマンド
```Bash
kemomctr glos /path/to/src/lang/ --tgt-dir /path/to/tgt/lang/ -o my_glossary.csv
```

オプション
- `src_dir` : (必須) 探索元のソースディレクトリパス
- `--tgt-dir` : (任意) 訳語を抽出するターゲットディレクトリパス
- `-o` / `--output` : 出力・追記するCSVのパス (デフォルト: glossary_generated.csv)
- `-s` / `--source` : 翻訳元の言語コード (デフォルト: en_us)
- `-t` / `--target` : 翻訳先の言語コード (デフォルト: ja_jp)

収集したCSVはそのまま、`tr` コマンドの `-g` オプションで利用可能です。また、指定した用語集は翻訳時に動的フィルタリングされるため、万単位の行数があってもAPIコンテキストを圧迫せず効率的に適用されます。


# 🗺️実装予定機能
- 既存の翻訳からのglossaryの自動生成および動的生成: 完了
- アップデートに対応するための差分翻訳(ソース言語の差分を確認して再度翻訳): 一部完了
- coremod等のjarを展開し翻訳する
- MC1.21以降のsnbt形式のlangファイルへの対応

プルリクエストやIssuesでの要望も歓迎しています。
