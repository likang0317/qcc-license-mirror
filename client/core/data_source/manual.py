"""手动导入：解析 CSV / Excel / 粘贴表格"""
import csv
import io
from pathlib import Path

from .base import DataSource, Contact


class ManualSource(DataSource):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def name(self) -> str:
        return "手动导入"

    def fetch(self, keyword: str = "", **kwargs) -> list[Contact]:
        """从文件路径或粘贴文本解析。kwargs: path= 或 text="""
        path = kwargs.get("path")
        text = kwargs.get("text")
        if path:
            return self._parse_file(path)
        if text:
            return self._parse_text(text)
        return []

    def _parse_file(self, path: str) -> list[Contact]:
        p = Path(path)
        if p.suffix.lower() in (".xlsx", ".xls"):
            return self._parse_excel(p)
        text = p.read_text(encoding="utf-8-sig")
        return self._parse_text(text)

    def _parse_excel(self, path: Path) -> list[Contact]:
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise RuntimeError("缺少 openpyxl: pip install openpyxl")
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        return self._rows_to_contacts(rows)

    def _parse_text(self, text: str) -> list[Contact]:
        """支持 tab 分隔 / 逗号分隔 / 每行一个手机号"""
        text = text.strip()
        if not text:
            return []
        # 尝试 CSV
        try:
            rows = list(csv.reader(io.StringIO(text), delimiter=","))
        except Exception:
            rows = [line.split("\t") for line in text.splitlines()]
        return self._rows_to_contacts(rows)

    def _rows_to_contacts(self, rows: list) -> list[Contact]:
        """自动识别表头，兼容任意列顺序"""
        if not rows:
            return []
        header = [str(c).strip() if c else "" for c in rows[0]]
        idx = self._detect_columns(header)
        data_rows = rows[1:] if idx else rows  # 无表头则全是数据
        out = []
        for row in data_rows:
            if not row:
                continue
            phone = str(row[idx["phone"]] or "").strip() if idx.get("phone") else ""
            if not phone or not phone.isdigit():
                # 可能这行本身就是纯手机号
                cell = str(row[0] or "").strip()
                if cell.isdigit() and len(cell) >= 7:
                    out.append(Contact(phone=cell))
                continue
            company = str(row[idx["company"]] or "").strip() if idx.get("company") else ""
            name = str(row[idx["name"]] or "").strip() if idx.get("name") else ""
            out.append(Contact(company=company, name=name, phone=phone))
        return out

    def _detect_columns(self, header: list[str]) -> dict:
        keys = {"company": ["企业", "公司", "单位", "company"],
                "name": ["姓名", "联系人", "name"],
                "phone": ["手机", "电话", "phone", "tel"]}
        idx = {}
        for key, aliases in keys.items():
            for i, h in enumerate(header):
                if any(a in h.lower() for a in aliases):
                    idx[key] = i
                    break
        return idx
