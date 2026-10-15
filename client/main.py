"""客户端主窗口骨架（Phase 2/3 逐步填充）"""
import sys
import os
from pathlib import Path

import yaml
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

from core.license.machine_id import get_device_id
from core.license.license_client import LicenseClient, LicenseError
from gui.register_dialog import RegisterDialog

CONFIG_PATH = str(Path(__file__).resolve().parent.parent / "config" / "settings.yaml")


def load_config() -> dict:
    if Path(CONFIG_PATH).exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


class MainWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self.setWindowTitle("企查查 → 微信 自动加好友")
        self.resize(960, 640)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("🚀 企查查 → 微信 自动加好友工具")
        title.setStyleSheet("font-size:22px;font-weight:600;")
        layout.addWidget(title)

        device = QLabel(f"设备 ID: {get_device_id()}")
        device.setStyleSheet("color:#888;font-size:12px;")
        layout.addWidget(device)

        layout.addStretch()

        # TODO: Phase 4 填充搜索面板、任务面板、日志面板
        placeholder = QLabel("🛠️  功能面板开发中...\nPhase 4 会补上企查查搜索 + 微信自动化")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color:#bbb;font-size:16px;border:2px dashed #eee;border-radius:12px;padding:40px;")
        placeholder.setMinimumHeight(280)
        layout.addWidget(placeholder)

        layout.addStretch()


def main():
    # 1. 读配置
    cfg = load_config()
    server_url = cfg.get("license_server_url", "http://localhost:8000")

    # 2. 授权检查
    app = QApplication(sys.argv)
    client = LicenseClient(server_url)
    device_id = get_device_id()

    # 2a. 没授权 → 弹注册窗
    local = None
    try:
        from core.license.local_store import load_license
        local = load_license(device_id, client.config_path)
    except Exception:
        local = None

    if not local:
        dialog = RegisterDialog(server_url)
        if dialog.exec_() != RegisterDialog.Accepted:
            QMessageBox.information(None, "提示", "未授权，软件退出")
            sys.exit(0)

    # 2b. 已授权 → 启动联网验证（不阻塞）
    status = client.verify(device_id, offline_ok=True)
    if status == "device_mismatch":
        QMessageBox.critical(None, "授权失效", "❌ 此授权已绑定其他设备，请联系管理员")
        sys.exit(1)
    if status == "revoked":
        QMessageBox.warning(None, "授权失效", "⚠️ 您的授权已被吊销，24 小时后将无法使用")
    # ok / offline 都放行

    # 3. 启动主窗口
    win = MainWindow(cfg)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
