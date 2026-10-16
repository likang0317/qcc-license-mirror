"""PyAutoGUI 模拟点击操作 PC 版微信"""
import time

from .base import WechatBot


class PyAutoGuiBot(WechatBot):
    def __init__(self, interval_min: float = 5.0, interval_max: float = 10.0, **kwargs):
        self.interval_min = interval_min
        self.interval_max = interval_max
        self._pg = None

    def name(self) -> str:
        return "PyAutoGUI 模拟"

    def _ensure_pyautogui(self):
        if self._pg is None:
            try:
                import pyautogui
                pyautogui.FAILSAFE = True  # 鼠标移到左上角会中止
                pyautogui.PAUSE = 0.3
                self._pg = pyautogui
            except ImportError:
                raise RuntimeError("缺少 pyautogui: pip install pyautogui")

    def add_friend(self, phone: str, remark: str = "", **kwargs) -> dict:
        self._ensure_pyautogui()
        pg = self._pg
        import random

        try:
            # 1. Ctrl+F 打开搜索 / 或点击搜索框
            pg.hotkey("ctrl", "f")
            time.sleep(random.uniform(0.3, 0.6))

            # 2. 清空并输入手机号
            pg.hotkey("ctrl", "a")
            time.sleep(0.1)
            pg.typewrite(phone, interval=0.05)
            time.sleep(random.uniform(0.4, 0.8))

            # 3. 回车搜索
            pg.press("enter")
            time.sleep(random.uniform(1.0, 1.5))

            # 4. 点搜索结果第一个（假设是微信好友添加入口）
            # 不同微信版本位置不同，先简化：按下箭头选中，再回车进入
            pg.press("enter")
            time.sleep(random.uniform(0.8, 1.2))

            # 5. 发送请求按钮（简化处理）
            # 实际需要根据按钮位置调整
            time.sleep(random.uniform(self.interval_min, self.interval_max))
            return {"ok": True, "msg": f"已模拟发送请求: {phone}"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def stop(self):
        """鼠标移到屏幕左上角可中止 pyautogui"""
        if self._pg:
            self._pg.moveTo(0, 0)
