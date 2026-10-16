"""微信自动化抽象接口"""
from abc import ABC, abstractmethod

class WechatBot(ABC):
    @abstractmethod
    def name(self) -> str:
        """显示名"""
        ...

    @abstractmethod
    def add_friend(self, phone: str, remark: str = "", **kwargs) -> dict:
        """加好友，返回 {ok: bool, msg: str}"""
        ...

    def batch_add(self, contacts: list, progress_cb=None) -> list[dict]:
        """批量加好友，progress_cb(i, total, contact)"""
        results = []
        total = len(contacts)
        for i, c in enumerate(contacts):
            if progress_cb:
                progress_cb(i, total, c)
            res = self.add_friend(c.phone, remark=c.name)
            results.append({"phone": c.phone, "name": c.name, **res})
        return results
