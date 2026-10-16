"""客户端入口"""
import sys
from pathlib import Path

import json
from PyQt5.QtWidgets import QApplication, QMessageBox

from core.license.machine_id import get_device_id
from core.license.license_client import LicenseClient
from gui.register_dialog import RegisterDialog
from gui.main_window import MainWindow

def _exe_dir() -> Path:
    """PyInstaller 打包后取 exe 所在目录，开发时取 main.py 所在目录。"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

CONFIG_PATH = str(_exe_dir() / "config" / "settings.json")


def load_config() -> dict:
    if Path(CONFIG_PATH).exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                pass
    return {"license_server_url": "http://localhost:8000"}


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
