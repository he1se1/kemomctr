import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QCheckBox,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from . import recursive_translator
from . import pack_maker
from . import single_translator
from . import glossary_maker


DARK_STYLE = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    color: #cdd6f4;
    font-family: "Segoe UI", "Yu Gothic UI", "Hiragino Sans", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 8px;
    background-color: #181825;
    padding: 15px;
}
QTabBar::tab {
    background-color: #313244;
    color: #a6adc8;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #89b4fa;
    color: #11111b;
}
QTabBar::tab:hover:!selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #89b4fa;
}
QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 14px;
    color: #cdd6f4;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton#runButton {
    background-color: #89b4fa;
    color: #11111b;
    border: none;
    font-size: 14px;
    font-weight: bold;
    padding: 12px 24px;
    border-radius: 8px;
}
QPushButton#runButton:hover {
    background-color: #b4befe;
}
QPushButton#runButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QLabel {
    color: #cdd6f4;
    font-weight: 500;
}
"""

class DropLineEdit(QLineEdit):
    """ファイル・フォルダのドラッグ＆ドロップに対応した入力フィールド"""
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.setText(path)


class WorkerThread(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, task_fn, *args, **kwargs):
        super().__init__()
        self.task_fn = task_fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.task_fn(*self.args, **self.kwargs)
            self.finished_signal.emit(True, "")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("kemomctr - Minecraft Mod AI Localization")
        self.resize(650, 480)
        self.setStyleSheet(DARK_STYLE)

        self.worker = None
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # タブエリア
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.setup_tr_tab()
        self.setup_col_tab()
        self.setup_glos_tab()

    def create_path_input(self, placeholder="", browse_type="dir", filter_str="All Files (*)"):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        line_edit = DropLineEdit(placeholder)
        layout.addWidget(line_edit)

        btn = QPushButton("参照")
        btn.setFixedWidth(70)

        if browse_type == "dir":
            btn.clicked.connect(lambda: self.browse_dir(line_edit))
        elif browse_type == "file":
            btn.clicked.connect(lambda: self.browse_file(line_edit, filter_str))
        elif browse_type == "save":
            btn.clicked.connect(lambda: self.save_file(line_edit, filter_str))

        layout.addWidget(btn)
        return layout, line_edit

    def browse_dir(self, line_edit):
        d = QFileDialog.getExistingDirectory(self, "ディレクトリを選択")
        if d:
            line_edit.setText(d)

    def browse_file(self, line_edit, filter_str):
        f, _ = QFileDialog.getOpenFileName(self, "ファイルを選択", filter=filter_str)
        if f:
            line_edit.setText(f)

    def save_file(self, line_edit, filter_str):
        f, _ = QFileDialog.getSaveFileName(self, "保存先を選択", filter=filter_str)
        if f:
            line_edit.setText(f)

    # --- 1. 翻訳 (tr) タブ ---
    def setup_tr_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        path_lay, self.tr_dir = self.create_path_input("フォルダをドロップまたは参照", "dir")
        form.addRow("対象ディレクトリ:", path_lay)

        self.tr_src = QLineEdit("en_us")
        form.addRow("翻訳元言語:", self.tr_src)

        self.tr_tgt = QLineEdit("ja_jp")
        form.addRow("翻訳先言語:", self.tr_tgt)

        gls_lay, self.tr_gls = self.create_path_input("CSVファイルをドロップまたは参照 (任意)", "file", "CSV Files (*.csv)")
        form.addRow("用語集CSV (任意):", gls_lay)

        ref_lay, self.tr_ref = self.create_path_input("旧Verフォルダをドロップまたは参照 (任意)", "dir")
        form.addRow("旧Verディレクトリ:", ref_lay)

        layout.addLayout(form)

        # オプション
        self.tr_no_sort = QCheckBox("キーの自動ソートを無効化 (--no-sort)")
        self.tr_flex = QCheckBox("Flexモードでリクエスト (--flex)")
        layout.addWidget(self.tr_no_sort)
        layout.addWidget(self.tr_flex)

        layout.addStretch()

        # 実行ボタン
        self.btn_tr_run = QPushButton("翻訳を実行")
        self.btn_tr_run.setObjectName("runButton")
        self.btn_tr_run.clicked.connect(self.run_tr)
        layout.addWidget(self.btn_tr_run, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tabs.addTab(tab, "🌐 翻訳 (tr)")

    def run_tr(self):
        arg_dir = self.tr_dir.text().strip()
        arg_src = self.tr_src.text().strip() or "en_us"
        arg_tgt = self.tr_tgt.text().strip() or "ja_jp"
        arg_gls = self.tr_gls.text().strip() or None
        arg_ref = self.tr_ref.text().strip() or None
        arg_no_sort = self.tr_no_sort.isChecked()
        arg_flex = self.tr_flex.isChecked()

        if not arg_dir:
            QMessageBox.critical(self, "エラー", "対象ディレクトリを指定してください。")
            return

        def task():
            single_translator.CANCEL_REQUESTED = False
            recursive_translator.run_recursive(
                arg_dir, arg_src, arg_tgt, arg_gls, arg_ref, arg_no_sort, arg_flex
            )

        self.start_worker(task, self.btn_tr_run, "翻訳処理が完了しました。")

    # --- 2. リソースパック生成 (col) タブ ---
    def setup_col_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        src_lay, self.col_src = self.create_path_input("検索元フォルダをドロップまたは参照", "dir")
        form.addRow("検索元ディレクトリ:", src_lay)

        dst_lay, self.col_dst = self.create_path_input("保存先フォルダをドロップまたは参照", "dir")
        form.addRow("保存先ディレクトリ:", dst_lay)

        self.col_ver = QLineEdit("1.20.1")
        form.addRow("MCバージョン:", self.col_ver)

        layout.addLayout(form)

        self.col_en = QCheckBox("en_us.json も収集・マージする (--en)")
        layout.addWidget(self.col_en)

        layout.addStretch()

        self.btn_col_run = QPushButton("パック生成を実行")
        self.btn_col_run.setObjectName("runButton")
        self.btn_col_run.clicked.connect(self.run_col)
        layout.addWidget(self.btn_col_run, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tabs.addTab(tab, "📦 リソースパック生成 (col)")

    def run_col(self):
        arg_src = self.col_src.text().strip()
        arg_dst = self.col_dst.text().strip()
        arg_en = self.col_en.isChecked()
        arg_ver = self.col_ver.text().strip() or "1.20.1"

        if not arg_src or not arg_dst:
            QMessageBox.critical(self, "エラー", "検索元と保存先ディレクトリの両方を指定してください。")
            return

        def task():
            pack_maker.run_pack_maker(arg_src, arg_dst, arg_en, arg_ver)

        self.start_worker(task, self.btn_col_run, "リソースパックの生成が完了しました。")

    # --- 3. 用語集生成 (glos) タブ ---
    def setup_glos_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        src_lay, self.glos_src_dir = self.create_path_input("原語側フォルダをドロップまたは参照", "dir")
        form.addRow("原語フォルダ(必須):", src_lay)

        tgt_lay, self.glos_tgt_dir = self.create_path_input("訳語側フォルダをドロップまたは参照 (任意)", "dir")
        form.addRow("訳語フォルダ(任意):", tgt_lay)

        dst_lay, self.glos_dst = self.create_path_input("出力CSVの保存先", "save", "CSV Files (*.csv)")
        self.glos_dst.setText("glossary_generated.csv")
        form.addRow("出力・追記先CSV:", dst_lay)

        self.glos_src = QLineEdit("en_us")
        form.addRow("原語の言語コード:", self.glos_src)

        self.glos_tgt = QLineEdit("ja_jp")
        form.addRow("訳語の言語コード:", self.glos_tgt)

        layout.addLayout(form)
        layout.addStretch()

        self.btn_glos_run = QPushButton("用語集生成を実行")
        self.btn_glos_run.setObjectName("runButton")
        self.btn_glos_run.clicked.connect(self.run_glos)
        layout.addWidget(self.btn_glos_run, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tabs.addTab(tab, "📚 用語集生成 (glos)")

    def run_glos(self):
        arg_src_dir = self.glos_src_dir.text().strip()
        arg_tgt_dir = self.glos_tgt_dir.text().strip() or None
        arg_dst = self.glos_dst.text().strip() or "glossary_generated.csv"
        arg_src = self.glos_src.text().strip() or "en_us"
        arg_tgt = self.glos_tgt.text().strip() or "ja_jp"

        if not arg_src_dir:
            QMessageBox.critical(self, "エラー", "ソースディレクトリを指定してください。")
            return

        def task():
            glossary_maker.run_glossary_maker(arg_src_dir, arg_tgt_dir, arg_dst, arg_src, arg_tgt)

        self.start_worker(task, self.btn_glos_run, "用語集の生成・追記が完了しました。")

    # --- 共通 Worker 管理 ---
    def start_worker(self, task_fn, run_btn, success_msg):
        run_btn.setEnabled(False)
        self.worker = WorkerThread(task_fn)

        def on_finished(success, err_msg):
            run_btn.setEnabled(True)
            single_translator.current_thread = None
            if success:
                if not getattr(single_translator, "CANCEL_REQUESTED", False):
                    QMessageBox.information(self, "完了", success_msg)
            else:
                QMessageBox.critical(self, "エラー", f"処理中にエラーが発生しました:\n{err_msg}")

        self.worker.finished_signal.connect(on_finished)
        single_translator.current_thread = self.worker
        self.worker.start()


def run_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())