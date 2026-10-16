"""企查查网页爬取（简单版，易触发滑块验证）"""
import re
import time
import urllib.parse

from .base import DataSource, Contact


class QccScrapeSource(DataSource):
    BASE = "https://www.qcc.com"

    def __init__(self, **kwargs):
        self.timeout = kwargs.get("timeout", 10)

    def name(self) -> str:
        return "企查查网页搜索"

    def fetch(self, keyword: str = "", **kwargs) -> list[Contact]:
        """按关键字搜索企业，返回带电话的联系人（可能需登录滑块）"""
        if not keyword:
            return []
        try:
            import requests
        except ImportError:
            raise RuntimeError("缺少 requests")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        url = f"{self.BASE}/web/search?key={urllib.parse.quote(keyword)}"
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
        except Exception as e:
            raise RuntimeError(f"企查查访问失败: {e}")

        if resp.status_code != 200:
            raise RuntimeError(f"企查查返回 {resp.status_code}，可能触发验证")

        return self._parse_search(resp.text)

    def _parse_search(self, html: str) -> list[Contact]:
        """从搜索页 HTML 里抓企业名和电话"""
        contacts = []
        # 企业名
        companies = re.findall(r'<a[^>]*title="([^"]+)"[^>]*href="/firm/', html)
        # 电话（模糊匹配手机号）
        phones = re.findall(r'1[3-9]\d{9}', html)
        for i, phone in enumerate(set(phones)):
            company = companies[i % len(companies)] if companies else ""
            contacts.append(Contact(company=company, phone=phone))
        return contacts
