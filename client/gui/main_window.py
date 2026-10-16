"""主窗口：数据源选择 + 名单表格 + 任务控制 + 日志"""
import threading
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTextEdit, QLineEdit, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QFrame,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor

from core.data_source import create as create_source
from core.wechat import create as create_wechat


# 数据源选项
SOURCE_OPTIONS = [
    ("手动导入", "manual"),
    ("企查查网页搜索", "qcc_scrape"),
    ("企查查开放API", "qcc_api"),
]

# 微信自动化选项
WX_OPTIONS = [
    ("生成 VCF 通讯录（最安全）", "vcf"),
    ("PyAutoGUI 模拟点击", "pyautogui"),
    ("网页版自动发", "itchat"),
]


class BatchThread(QThread):
    """后台批量添加线程"""
    progress = pyqtSignal(int, int, str)  # done, total, phone
    log = pyqtSignal(str)                  # 日志
    finished_ok = pyqtSignal(list)         # 结果列表

    def __init__(self, wechat_bot, contacts):
        super().__init__()
        self.bot = wechat_bot
        self.contacts = contacts
        self._stop = False

    def run(self):
        results = []
        total = len(self.contacts)
        for i, c in enumerate(self.contacts):
            if self._stop:
                self.log.emit("⏹ 任务已停止")
                break
            self.progress.emit(i, total, c.phone)
            self.log.emit(f"▶ {i+1}/{total} {c.company or '-'} {c.name or '-'} {c.phone}")
            try:
                res = self.bot.add_friend(c.phone, remark=c.name)
            except Exception as e:
                res = {"ok": False, "msg": str(e)}
            results.append({**{"company": c.company, "name": c.name, "phone": c.phone}, **res})
            icon = "✅" if res.get("ok") else "❌"
            self.log.emit(f"  {icon} {res.get('msg', '')}")
        self.finished_ok.emit(results)

    def stop(self):
        self._stop = True


# 统一样式
_COMBO_STYLE = """
QComboBox { padding:6px 12px; border:1px solid #d1d5db; border-radius:6px;
             font-size:14px; background:#fff; min-height:24px; }
QComboBox:hover { border-color:#0FDC78; }
QComboBox:focus { border-color:#0FDC78; }
QComboBox::drop-down { border:none; width:28px; }
QComboBox QAbstractItemView { border:1px solid #d1d5db; border-radius:6px;
                              background:#fff; selection-background-color:#0FDC78;
                              selection-color:#004D26; outline:none; }
"""
_BTN_OUTLINE = """
QPushButton { padding:6px 14px; border:1px solid #d1d5db; border-radius:6px;
              font-size:13px; background:#fff; min-height:24px; }
QPushButton:hover { border-color:#0FDC78; color:#0FDC78; }
QPushButton:disabled { background:#f9fafb; color:#c0c0c0; border-color:#eee; }
"""
_LABEL_STYLE = "font-size:13px; color:#374151;"


class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._contacts = []
        self._worker: BatchThread | None = None
        self.setWindowTitle("企查查 → 微信 自动加好友工具")
        self.resize(1100, 720)
        self._build_ui()

    # ========== UI ==========
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        # 顶部标题
        title_row = QHBoxLayout()
        title = QLabel("🚀 企查查 → 微信 自动加好友")
        title.setStyleSheet("font-size:18px;font-weight:600;")
        title_row.addWidget(title)
        title_row.addStretch()
        root.addLayout(title_row)

        # 配置栏
        cfg = QFrame()
        cfg.setFrameShape(QFrame.StyledPanel)
        cfg.setStyleSheet("QFrame { background:#fafafa; border:1px solid #eee; border-radius:6px; }")
        cfg_layout = QVBoxLayout(cfg)
        cfg_layout.setContentsMargins(16, 14, 16, 14)
        cfg_layout.setSpacing(12)

        # 第一行：两个下拉框
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        row1.addWidget(QLabel("数据源:"), 0, Qt.AlignVCenter)
        self.source_combo = QComboBox()
        for label, val in SOURCE_OPTIONS:
            self.source_combo.addItem(label, val)
        self.source_combo.setStyleSheet(_COMBO_STYLE)
        self.source_combo.setMinimumWidth(200)
        row1.addWidget(self.source_combo, 0)
        row1.addSpacing(24)
        row1.addWidget(QLabel("微信自动化:"), 0, Qt.AlignVCenter)
        self.wx_combo = QComboBox()
        for label, val in WX_OPTIONS:
            self.wx_combo.addItem(label, val)
        self.wx_combo.setStyleSheet(_COMBO_STYLE)
        self.wx_combo.setMinimumWidth(240)
        row1.addWidget(self.wx_combo, 0)
        row1.addStretch()
        cfg_layout.addLayout(row1)

        # 第二行：三个按钮
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.import_btn = QPushButton("📂 导入名单")
        self.import_btn.setStyleSheet(_BTN_OUTLINE)
        self.import_btn.setMinimumHeight(32)
        self.import_btn.clicked.connect(self._on_import)
        row2.addWidget(self.import_btn)

        self.paste_btn = QPushButton("📋 粘贴导入")
        self.paste_btn.setStyleSheet(_BTN_OUTLINE)
        self.paste_btn.setMinimumHeight(32)
        self.paste_btn.clicked.connect(self._on_paste)
        row2.addWidget(self.paste_btn)

        self.search_btn = QPushButton("🔍 企查查搜索")
        self.search_btn.setStyleSheet(_BTN_OUTLINE)
        self.search_btn.setMinimumHeight(32)
        self.search_btn.clicked.connect(self._on_search)
        row2.addWidget(self.search_btn)

        row2.addStretch()
        cfg_layout.addLayout(row2)

        # 名单表格
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["序号", "企业名称", "联系人", "电话号码", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget { gridline-color:#eee; font-size:13px; }")
        root.addWidget(self.table, stretch=1)

        # 底部：进度条 + 控制按钮 + 日志
        bottom = QVBoxLayout()
        bottom.setSpacing(8)

        ctrl_row = QHBoxLayout()
        self.start_btn = QPushButton("▶ 开始")
        self.start_btn.setStyleSheet("padding:8px 20px;background:#0FDC78;color:#004D26;border:none;border-radius:6px;font-weight:600;")
        self.start_btn.clicked.connect(self._on_start)

        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setStyleSheet("padding:8px 20px;background:#FEF3C7;color:#78350F;border:none;border-radius:6px;font-weight:600;")
        self.pause_btn.setEnabled(False)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet("padding:8px 20px;background:#E8463A;color:#fff;border:none;border-radius:6px;font-weight:600;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)

        ctrl_row.addWidget(self.start_btn)
        ctrl_row.addWidget(self.pause_btn)
        ctrl_row.addWidget(self.stop_btn)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("0/0")
        ctrl_row.addWidget(self.progress, stretch=1)
        bottom.addLayout(ctrl_row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        self.log.setStyleSheet("font-family:Consolas,monospace;font-size:12px;background:#f9fafb;border:1px solid #eee;border-radius:6px;")
        bottom.addWidget(self.log)

        root.addLayout(bottom)

    # ========== 事件 ==========
    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 Excel/CSV", "", "表格文件 (*.csv *.xlsx *.xls);;所有文件 (*)")
        if not path:
            return
        try:
            src = create_source(self.source_combo.currentData())
            contacts = src.fetch(path=path)
            self._set_contacts(contacts)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _on_paste(self):
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(self, "粘贴名单", "从 Excel 复制粘贴（每行一条，支持 tab/逗号分隔）:")
        if not ok or not text.strip():
            return
        try:
            src = create_source(self.source_combo.currentData())
            contacts = src.fetch(text=text)
            self._set_contacts(contacts)
        except Exception as e:
            QMessageBox.critical(self, "粘贴失败", str(e))

    def _on_search(self):
        from PyQt5.QtWidgets import QInputDialog
        keyword, ok = QInputDialog.getText(self, "企查查搜索", "关键字（如：上海 科技）:")
        if not ok or not keyword.strip():
            return
        try:
            src = create_source(self.source_combo.currentData(),
                                api_key=self._config.get("qcc_api_key", ""),
                                api_secret=self._config.get("qcc_api_secret", ""))
            contacts = src.fetch(keyword=keyword.strip())
            self._set_contacts(contacts)
        except Exception as e:
            QMessageBox.critical(self, "搜索失败", str(e))

    def _set_contacts(self, contacts: list):
        self._contacts = contacts
        self.table.setRowCount(len(contacts))
        for i, c in enumerate(contacts):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(c.company))
            self.table.setItem(i, 2, QTableWidgetItem(c.name))
            self.table.setItem(i, 3, QTableWidgetItem(c.phone))
            status = QTableWidgetItem("⏳ 待加")
            status.setForeground(QColor("#888"))
            self.table.setItem(i, 4, status)
        self._log(f"📋 已载入 {len(contacts)} 条联系人")
        self.progress.setMaximum(len(contacts))
        self.progress.setValue(0)

    def _on_start(self):
        if not self._contacts:
            QMessageBox.information(self, "提示", "请先导入或搜索联系人")
            return
        wechat_type = self.wx_combo.currentData()
        try:
            bot = create_wechat(wechat_type)
        except Exception as e:
            QMessageBox.critical(self, "初始化失败", str(e))
            return
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._worker = BatchThread(bot, self._contacts)
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._log)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.start()

    def _on_stop(self):
        if self._worker:
            self._worker.stop()

    def _on_progress(self, done: int, total: int, phone: str):
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.progress.setFormat(f"{done}/{total}")
        # 更新表格状态
        row = done
        if 0 <= row < self.table.rowCount():
            status_item = self.table.item(row, 4)
            if status_item:
                status_item.setText("🔄 处理中")
                status_item.setForeground(QColor("#3B82F6"))
            self.table.scrollToItem(status_item)

    def _on_done(self, results: list):
        for i, r in enumerate(results):
            if i >= self.table.rowCount():
                break
            item = self.table.item(i, 4)
            if item:
                if r.get("ok"):
                    item.setText("✅ 完成")
                    item.setForeground(QColor("#059669"))
                else:
                    item.setText("❌ 失败")
                    item.setForeground(QColor("#E8463A"))
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(self.progress.maximum())
        self._log(f"🏁 任务完成，共 {len(results)} 条")

    def _log(self, msg: str):
        self.log.append(msg)
