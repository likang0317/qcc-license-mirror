"""itchat / wechaty 网页版（标记实现）"""
from .base import WechatBot


class ItchatBot(WechatBot):
    def __init__(self, **kwargs):
        self.itchat = None
        self.logged_in = False

    def name(self) -> str:
        return "网页版自动发"

    def login(self) -> bool:
        """扫码登录（首次使用）"""
        try:
            import itchat
        except ImportError:
            raise RuntimeError("缺少 itchat: pip install itchat-uos")
        import io
        # 让用户扫码
        itchat.auto_login(enableCmdQR=2, hotReload=True)
        self.itchat = itchat
        self.logged_in = True
        return True

    def add_friend(self, phone: str, remark: str = "", **kwargs) -> dict:
        if not self.logged_in:
            return {"ok": False, "msg": "未登录，请先扫码"}
        try:
            # itchat 已停更，这里仅做骨架
            friends = self.itchat.search_friends(name=phone)
            # ... 添加好友
            return {"ok": True, "msg": f"已请求: {phone}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}
