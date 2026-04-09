"""
kemomctr グラフィカルユーザーインターフェース (Tkinter)
各サブコマンドに対応したタブを提供し、バックグラウンドスレッドで処理を実行する
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from . import recursive_translator
from . import pack_maker
from . import single_translator
from . import glossary_maker
from . import format_handlers

def run_gui():
    """メインウィンドウを生成して実行する"""
    root = tk.Tk()
    root.title("kemomctr - Minecraft Mod Translation Suite")
    root.geometry("650x450")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both", padx=10, pady=10)

    # ---------------------------------------------------------
    # 共通ヘルパー関数
    # ---------------------------------------------------------
    
    def browse_dir(entry):
        d = filedialog.askdirectory()
        if d:
            entry.delete(0, tk.END)
            entry.insert(0, d)

    def browse_file(entry):
        f = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if f:
            entry.delete(0, tk.END)
            entry.insert(0, f)

    def save_file(entry):
        f = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if f:
            entry.delete(0, tk.END)
            entry.insert(0, f)

    def create_input_row(parent, label, row, browse_type=None, default_val=""):
        """ラベル、入力フィールド、参照ボタンの1行を作成する"""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", padx=5, pady=5)
        entry = ttk.Entry(parent, width=45)
        entry.grid(row=row, column=1, padx=5, pady=5)
        if default_val:
            entry.insert(0, default_val)
        
        if browse_type == "dir":
            ttk.Button(parent, text="参照", command=lambda: browse_dir(entry)).grid(row=row, column=2, padx=5)
        elif browse_type == "file":
            ttk.Button(parent, text="参照", command=lambda: browse_file(entry)).grid(row=row, column=2, padx=5)
        elif browse_type == "save":
            ttk.Button(parent, text="参照", command=lambda: save_file(entry)).grid(row=row, column=2, padx=5)
        return entry

    def create_format_selector(parent, row, variable):
        """サポートされているフォーマットのラジオボタン行を作成する"""
        ttk.Label(parent, text="フォーマット:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        fmt_frame = ttk.Frame(parent)
        fmt_frame.grid(row=row, column=1, sticky="w", padx=5)
        for f in format_handlers.get_supported_formats():
            ttk.Radiobutton(fmt_frame, text=f, variable=variable, value=f).pack(side="left", padx=2)

    # ---------------------------------------------------------
    # 翻訳 (tr) タブ
    # ---------------------------------------------------------
    frame_tr = ttk.Frame(notebook)
    notebook.add(frame_tr, text="翻訳 (tr)")

    tr_dir = create_input_row(frame_tr, "対象ディレクトリ:", 0, "dir")
    tr_src = create_input_row(frame_tr, "翻訳元言語:", 1, default_val="en_us")
    tr_tgt = create_input_row(frame_tr, "翻訳先言語:", 2, default_val="ja_jp")
    tr_gls = create_input_row(frame_tr, "用語集CSV(任意):", 3, "file")
    tr_ref = create_input_row(frame_tr, "旧Verディレクトリ(任意):", 4, "dir")
    tr_prompt = create_input_row(frame_tr, "プロンプトFile(任意):", 5, "file")
    
    tr_format_var = tk.StringVar(value="json")
    create_format_selector(frame_tr, 6, tr_format_var)

    tr_no_sort_var = tk.BooleanVar()
    ttk.Checkbutton(frame_tr, text="キーの自動ソートを無効化 (--no-sort)", variable=tr_no_sort_var).grid(row=7, column=1, sticky="w", pady=5)

    def execute_tr():
        """翻訳タスクをサブスレッドで開始する"""
        arg_dir = tr_dir.get()
        arg_src = tr_src.get() or "en_us"
        arg_tgt = tr_tgt.get() or "ja_jp"
        arg_gls = tr_gls.get() or None
        arg_ref = tr_ref.get() or None
        arg_prompt_path = tr_prompt.get() or None
        arg_no_sort = tr_no_sort_var.get()
        arg_fmt = tr_format_var.get()

        if not arg_dir:
            messagebox.showerror("エラー", "対象ディレクトリを指定してください。")
            return
        
        # カスタムプロンプトの読み込み
        arg_prompt_content = None
        if arg_prompt_path:
            try:
                if os.path.exists(arg_prompt_path):
                    with open(arg_prompt_path, "r", encoding="utf-8") as f:
                        arg_prompt_content = f.read()
                else:
                    messagebox.showwarning("警告", "指定されたプロンプトファイルが見つかりません。デフォルトを使用します。")
            except Exception as e:
                messagebox.showerror("エラー", f"プロンプトファイルの読み込み失敗:\n{e}")
                return
        
        btn_tr_run.config(state="disabled")
        btn_tr_stop.config(state="normal")
        
        def task():
            try:
                single_translator.CANCEL_REQUESTED = False
                recursive_translator.run_recursive(
                    arg_dir, arg_src, arg_tgt, arg_gls, arg_ref, arg_no_sort, arg_fmt, arg_prompt_content
                )
                if not single_translator.CANCEL_REQUESTED:
                    messagebox.showinfo("完了", "翻訳処理が完了しました。")
                else:
                    messagebox.showinfo("中断", "翻訳を中断し、そこまでの結果を保存しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"処理中エラー:\n{e}")
            finally:
                try:
                    btn_tr_run.config(state="normal")
                    btn_tr_stop.config(state="disabled")
                except Exception:
                    pass
                single_translator.current_thread = None
                
        t = threading.Thread(target=task, daemon=True)
        single_translator.current_thread = t
        t.start()

    def stop_tr():
        """実行中の翻訳に中断リクエストを送信する"""
        if single_translator.current_thread and single_translator.current_thread.is_alive():
            single_translator.CANCEL_REQUESTED = True
            btn_tr_stop.config(state="disabled")

    btn_frame = ttk.Frame(frame_tr)
    btn_frame.grid(row=8, column=1, pady=15)
    btn_tr_run = ttk.Button(btn_frame, text="翻訳を実行", command=execute_tr)
    btn_tr_run.pack(side="left", padx=5)
    btn_tr_stop = ttk.Button(btn_frame, text="中断して保存", command=stop_tr, state="disabled")
    btn_tr_stop.pack(side="left", padx=5)

    # ---------------------------------------------------------
    # 収集 (col) タブ
    # ---------------------------------------------------------
    frame_col = ttk.Frame(notebook)
    notebook.add(frame_col, text="パック生成 (col)")

    col_src = create_input_row(frame_col, "検索元ディレクトリ:", 0, "dir")
    col_dst = create_input_row(frame_col, "保存先ディレクトリ:", 1, "dir")
    col_mc_ver = create_input_row(frame_col, "MCバージョン:", 2, default_val="1.20.1")

    col_format_var = tk.StringVar(value="json")
    create_format_selector(frame_col, 3, col_format_var)

    col_en_var = tk.BooleanVar()
    ttk.Checkbutton(frame_col, text="en_us(または相当) も収集・マージする (--en)", variable=col_en_var).grid(row=4, column=1, sticky="w", pady=5)

    def execute_col():
        arg_src = col_src.get()
        arg_dst = col_dst.get()
        arg_en = col_en_var.get()
        arg_ver = col_mc_ver.get() or "1.20.1"
        arg_fmt = col_format_var.get()

        if not arg_src or not arg_dst:
            messagebox.showerror("エラー", "検索元と保存先の両方を指定してください。")
            return

        btn_col_run.config(state="disabled")

        def task():
            try:
                pack_maker.run_pack_maker(arg_src, arg_dst, arg_en, arg_ver, arg_fmt)
                messagebox.showinfo("完了", "リソースパック生成完了。")
            except Exception as e:
                messagebox.showerror("エラー", f"生成失敗:\n{e}")
            finally:
                try:
                    btn_col_run.config(state="normal")
                except Exception: pass

        threading.Thread(target=task, daemon=True).start()

    btn_col_run = ttk.Button(frame_col, text="パック生成を実行", command=execute_col)
    btn_col_run.grid(row=5, column=1, pady=15)

    # ---------------------------------------------------------
    # 用語集生成 (glos) タブ
    # ---------------------------------------------------------
    frame_glos = ttk.Frame(notebook)
    notebook.add(frame_glos, text="用語集生成 (glos)")

    glos_src_dir = create_input_row(frame_glos, "ソースディレクトリ:", 0, "dir")
    glos_tgt_dir = create_input_row(frame_glos, "ターゲットディレクトリ:", 1, "dir")
    glos_dst = create_input_row(frame_glos, "出力・追記先CSV:", 2, "save", default_val="glossary_generated.csv")
    glos_src = create_input_row(frame_glos, "翻訳元言語:", 3, default_val="en_us")
    glos_tgt = create_input_row(frame_glos, "翻訳先言語:", 4, default_val="ja_jp")

    glos_format_var = tk.StringVar(value="json")
    create_format_selector(frame_glos, 5, glos_format_var)

    def execute_glos():
        arg_src_dir = glos_src_dir.get()
        arg_tgt_dir = glos_tgt_dir.get() or None
        arg_dst = glos_dst.get() or "glossary_generated.csv"
        arg_src = glos_src.get() or "en_us"
        arg_tgt = glos_tgt.get() or "ja_jp"
        arg_fmt = glos_format_var.get()

        if not arg_src_dir:
            messagebox.showerror("エラー", "ソースディレクトリを指定してください。")
            return

        btn_glos_run.config(state="disabled")

        def task():
            try:
                glossary_maker.run_glossary_maker(arg_src_dir, arg_tgt_dir, arg_dst, arg_src, arg_tgt, arg_fmt)
                messagebox.showinfo("完了", "用語集の生成・追記が完了しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"生成失敗:\n{e}")
            finally:
                try: btn_glos_run.config(state="normal")
                except Exception: pass

        threading.Thread(target=task, daemon=True).start()

    btn_glos_run = ttk.Button(frame_glos, text="用語集生成を実行", command=execute_glos)
    btn_glos_run.grid(row=6, column=1, pady=15)

    # ---------------------------------------------------------
    # 終了処理 (中断待機ロジック)
    # ---------------------------------------------------------
    
    def on_closing():
        """ウィンドウを閉じる際、実行中の翻訳があれば保存を待機する"""
        if single_translator.current_thread and single_translator.current_thread.is_alive():
            if messagebox.askokcancel("終了", "翻訳が実行中です。中断して保存してから終了しますか？"):
                single_translator.CANCEL_REQUESTED = True
                
                def wait_and_exit(count=0):
                    # 最大60秒待機
                    if single_translator.current_thread and single_translator.current_thread.is_alive() and count < 120:
                        if count % 2 == 0:
                            print(f"[GUI] 残りデータの保存を待機中... ({count//2}s elapsed)")
                        root.after(500, lambda: wait_and_exit(count + 1))
                    else:
                        root.destroy()
                wait_and_exit()
                return
            else:
                return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()