"""注册弹窗：用户输入 用户名 + 手机号 + 可选邀请码"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator

from core.license.machine_id import get_device_id
from core.license.license_client import LicenseClient, LicenseError


class RegisterDialog(QDialog):
    def __init__(self, server_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("软件注册")
        self.setMinimumSize(480, 400)
        self.resize(480, 400)
        self._server_url = server_url
        self._license_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        title = QLabel("🔐 软件授权注册")
        title.setStyleSheet("font-size:18px;font-weight:600;")
        layout.addWidget(title)

        tip = QLabel("首次使用需要注册授权，信息仅用于绑定您的设备")
        tip.setStyleSheet("color:#888;font-size:12px;")
        layout.addWidget(tip)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#eee;")
        layout.addWidget(sep)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("请输入用户名")
        self._username_edit.setFixedHeight(36)
        self._username_edit.setStyleSheet(
            "QLineEdit { padding:6px 12px; border:1px solid #d1d5db;"
            "border-radius:6px; font-size:14px; background:#fff; }"
            "QLineEdit:focus { border-color:#0FDC78; }"
        )
        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self._username_edit)

        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText("请输入手机号")
        self._phone_edit.setFixedHeight(36)
        self._phone_edit.setMaxLength(11)
        self._phone_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]+")))
        self._phone_edit.setStyleSheet(
            "QLineEdit { padding:6px 12px; border:1px solid #d1d5db;"
            "border-radius:6px; font-size:14px; background:#fff; }"
            "QLineEdit:focus { border-color:#0FDC78; }"
        )
        layout.addWidget(QLabel("手机号"))
        layout.addWidget(self._phone_edit)

        self._invite_edit = QLineEdit()
        self._invite_edit.setPlaceholderText("邀请码（可不填，服务端自动生成）")
        self._invite_edit.setFixedHeight(36)
        self._invite_edit.setStyleSheet(
            "QLineEdit { padding:6px 12px; border:1px solid #d1d5db;"
            "border-radius:6px; font-size:14px; background:#fff; }"
            "QLineEdit:focus { border-color:#0FDC78; }"
        )
        layout.addWidget(QLabel("邀请码（可选）"))
        layout.addWidget(self._invite_edit)

        self._device_label = QLabel(f"本机设备 ID：{get_device_id()[:16]}…")
        self._device_label.setStyleSheet("color:#aaa;font-size:11px;")
        layout.addWidget(self._device_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._register_btn = QPushButton("立即注册")
        self._register_btn.setStyleSheet(
            "background:#0FDC78;color:#004D26;border:none;"
            "padding:8px 28px;border-radius:6px;font-weight:600;"
        )
        self._register_btn.clicked.connect(self._on_register)
        btn_row.addWidget(self._register_btn)
        layout.addLayout(btn_row)

    def _on_register(self):
        username = self._username_edit.text().strip()
        phone = self._phone_edit.text().strip()
        invite = self._invite_edit.text().strip() or None

        if not username or not phone:
            QMessageBox.warning(self, "提示", "用户名和手机号不能为空")
            return
        if len(phone) != 11:
            QMessageBox.warning(self, "提示", "手机号格式不正确")
            return

        self._register_btn.setEnabled(False)
        self._register_btn.setText("注册中...")
        QApplication = None  # noqa - 避免循环导入
        # 实际写的时候直接用 QApplication.processEvents()

        try:
            client = LicenseClient(self._server_url)
            result = client.register(username, phone, get_device_id(), invite)
            self._license_id = result["license_id"]
            QMessageBox.information(self, "注册成功", "✅ 授权注册成功！\n您现在可以永久使用本软件了。")
            self.accept()
        except LicenseError as e:
            QMessageBox.critical(self, "注册失败", f"❌ {e}")
        except Exception as e:
            QMessageBox.critical(self, "网络错误", f"无法连接到授权服务器：{e}")
        finally:
            self._register_btn.setEnabled(True)
            self._register_btn.setText("立即注册")

    def get_license_id(self) -> str | None:
        return self._license_id
