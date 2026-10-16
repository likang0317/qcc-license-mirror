"""企查查开放 API（稳定但需 key）"""
from .base import DataSource, Contact


class QccApiSource(DataSource):
    API_SEARCH = "https://api.qcc.com/api/enterprise/search"

    def __init__(self, api_key: str = "", api_secret: str = "", **kwargs):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = kwargs.get("timeout", 10)

    def name(self) -> str:
        return "企查查开放API"

    def fetch(self, keyword: str = "", **kwargs) -> list[Contact]:
        if not keyword:
            return []
        if not self.api_key:
            raise RuntimeError("未配置 qcc_api_key")
        try:
            import requests
        except ImportError:
            raise RuntimeError("缺少 requests")

        try:
            resp = requests.post(
                self.API_SEARCH,
                json={"keyWord": keyword, "pageSize": kwargs.get("page_size", 20)},
                headers={"appKey": self.api_key},
                timeout=self.timeout,
            )
        except Exception as e:
            raise RuntimeError(f"企查查API失败: {e}")

        if resp.status_code != 200:
            raise RuntimeError(f"API 返回 {resp.status_code}")

        data = resp.json()
        items = (data.get("Result") or {}).get("Items") or []
        out = []
        for it in items:
            out.append(Contact(
                company=it.get("EntName", ""),
                phone=it.get("ContactNumber") or it.get("TelNumber") or "",
                name="",
            ))
        return out
