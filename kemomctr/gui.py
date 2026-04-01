import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from . import recursive_translator
from . import pack_maker
from . import single_translator
from . import glossary_maker

def run_gui():
    root = tk.Tk()
    root.title("kemomctr")
    root.geometry("600x400")

    after_id = None
    def check_signals():
        nonlocal after_id
        after_id = root.after(200, check_signals)
    check_signals()
    
    def on_closing():
        if after_id:
            root.after_cancel(after_id)
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both", padx=10, pady=10)

    # --- 翻訳 (tr) タブ ---
    frame_tr = ttk.Frame(notebook)
    notebook.add(frame_tr, text="翻訳 (tr)")

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

    tr_dir = create_input_row(frame_tr, "対象ディレクトリ:", 0, "dir")
    tr_src = create_input_row(frame_tr, "翻訳元言語:", 1, default_val="en_us")
    tr_tgt = create_input_row(frame_tr, "翻訳先言語:", 2, default_val="ja_jp")
    tr_gls = create_input_row(frame_tr, "用語集CSV(任意):", 3, "file")
    tr_ref = create_input_row(frame_tr, "旧Verディレクトリ(任意):", 4, "dir")
    tr_no_sort_var = tk.BooleanVar()
    ttk.Checkbutton(frame_tr, text="キーの自動ソートを無効化 (--no-sort)", variable=tr_no_sort_var).grid(row=5, column=1, sticky="w", pady=5)

    def execute_tr():
        arg_dir = tr_dir.get()
        arg_src = tr_src.get() or "en_us"
        arg_tgt = tr_tgt.get() or "ja_jp"
        arg_gls = tr_gls.get() or None
        arg_ref = tr_ref.get() or None
        arg_no_sort = tr_no_sort_var.get()

        if not arg_dir:
            messagebox.showerror("エラー", "対象ディレクトリを指定してください。")
            return
        
        btn_tr_run.config(state="disabled")
        
        def task():
            try:
                single_translator.CANCEL_REQUESTED = False
                recursive_translator.run_recursive(
                    arg_dir, arg_src, arg_tgt, arg_gls, arg_ref, arg_no_sort
                )
                if not single_translator.CANCEL_REQUESTED:
                    messagebox.showinfo("完了", "翻訳処理が完了しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
            finally:
                # GUIがすでに破棄されている場合はエラーを出さずにスルーする
                try:
                    btn_tr_run.config(state="normal")
                except Exception:
                    pass
                single_translator.current_thread = None
                
        t = threading.Thread(target=task, daemon=True)
        single_translator.current_thread = t
        t.start()

    btn_tr_run = ttk.Button(frame_tr, text="翻訳を実行", command=execute_tr)
    btn_tr_run.grid(row=6, column=1, pady=15)

    # --- 収集 (col) タブ ---
    frame_col = ttk.Frame(notebook)
    notebook.add(frame_col, text="リソースパック生成 (col)")

    col_src = create_input_row(frame_col, "検索元ディレクトリ:", 0, "dir")
    col_dst = create_input_row(frame_col, "保存先ディレクトリ:", 1, "dir")
    col_mc_ver = create_input_row(frame_col, "MCバージョン:", 2, default_val="1.20.1")

    col_en_var = tk.BooleanVar()
    ttk.Checkbutton(frame_col, text="en_us.json も収集・マージする (--en)", variable=col_en_var).grid(row=3, column=1, sticky="w", pady=5)

    def execute_col():
        arg_src = col_src.get()
        arg_dst = col_dst.get()
        arg_en = col_en_var.get()
        arg_ver = col_mc_ver.get() or "1.20.1"

        if not arg_src or not arg_dst:
            messagebox.showerror("エラー", "検索元と保存先ディレクトリの両方を指定してください。")
            return

        btn_col_run.config(state="disabled")

        def task():
            try:
                pack_maker.run_pack_maker(arg_src, arg_dst, arg_en, arg_ver)
                messagebox.showinfo("完了", "リソースパックの生成が完了しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
            finally:
                # こちらも同様の安全策を追加
                try:
                    btn_col_run.config(state="normal")
                except Exception:
                    pass

        threading.Thread(target=task, daemon=True).start()

    btn_col_run = ttk.Button(frame_col, text="パック生成を実行", command=execute_col)
    btn_col_run.grid(row=4, column=1, pady=15)

    # --- 用語集生成 (glos) タブ ---
    frame_glos = ttk.Frame(notebook)
    notebook.add(frame_glos, text="用語集生成 (glos)")

    glos_src_dir = create_input_row(frame_glos, "ソースディレクトリ(必須):", 0, "dir")
    glos_tgt_dir = create_input_row(frame_glos, "ターゲットディレクトリ(任意):", 1, "dir")
    glos_dst = create_input_row(frame_glos, "出力・追記先CSV:", 2, "save", default_val="glossary_generated.csv")
    glos_src = create_input_row(frame_glos, "翻訳元言語:", 3, default_val="en_us")
    glos_tgt = create_input_row(frame_glos, "翻訳先言語:", 4, default_val="ja_jp")

    def execute_glos():
        arg_src_dir = glos_src_dir.get()
        arg_tgt_dir = glos_tgt_dir.get() or None
        arg_dst = glos_dst.get() or "glossary_generated.csv"
        arg_src = glos_src.get() or "en_us"
        arg_tgt = glos_tgt.get() or "ja_jp"

        if not arg_src_dir:
            messagebox.showerror("エラー", "ソースディレクトリを指定してください。")
            return

        btn_glos_run.config(state="disabled")

        def task():
            try:
                glossary_maker.run_glossary_maker(arg_src_dir, arg_tgt_dir, arg_dst, arg_src, arg_tgt)
                messagebox.showinfo("完了", "用語集の生成・追記が完了しました。")
            except Exception as e:
                messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
            finally:
                try:
                    btn_glos_run.config(state="normal")
                except Exception:
                    pass

        threading.Thread(target=task, daemon=True).start()

    btn_glos_run = ttk.Button(frame_glos, text="用語集生成を実行", command=execute_glos)
    btn_glos_run.grid(row=5, column=1, pady=15)

    root.mainloop()