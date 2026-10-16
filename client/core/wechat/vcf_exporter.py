"""生成 vCard 文件 → 用户导入手机通讯录，微信自动推荐好友（零封号风险）"""
import io
from datetime import datetime
from pathlib import Path

from .base import WechatBot
from ..data_source.base import Contact


def _vcard(c: Contact) -> str:
    lines = ["BEGIN:VCARD", "VERSION:3.0"]
    if c.name:
        lines.append(f"N:{c.name};;;")
        lines.append(f"FN:{c.name}")
    if c.phone:
        lines.append(f"TEL;TYPE=CELL:{c.phone}")
    if c.company:
        lines.append(f"ORG:{c.company}")
    lines.append(f"NOTE:企查查导入 - {c.company}")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


class VcfExporter(WechatBot):
    def __init__(self, output_dir: str | None = None, **kwargs):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path.home() / "Contacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def name(self) -> str:
        return "生成 VCF 通讯录"

    def add_friend(self, phone: str, remark: str = "", **kwargs) -> dict:
        """单条追加到 vcf 文件"""
        contact = Contact(phone=phone, name=remark)
        return self.batch_add([contact])[0]

    def batch_add(self, contacts: list, progress_cb=None) -> list[dict]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        vcf_path = self.output_dir / f"qcc_{ts}.vcf"
        total = len(contacts)
        vcfs = []
        for i, c in enumerate(contacts):
            if progress_cb:
                progress_cb(i, total, c)
            vcfs.append(_vcard(c))
        vcf_path.write_text("\r\n".join(vcfs), encoding="utf-8")
        msg = f"已生成 {len(vcfs)} 个联系人 → {vcf_path}"
        import pyperclip
        try:
            pyperclip.copy(str(vcf_path))
        except Exception:
            pass
        return [{"ok": True, "msg": msg, "vcf": str(vcf_path)} for _ in contacts]
