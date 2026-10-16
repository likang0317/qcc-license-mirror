"""微信自动化工厂"""
from .base import WechatBot
from .pyautogui_bot import PyAutoGuiBot
from .itchat_bot import ItchatBot
from .vcf_exporter import VcfExporter

BOTS = {
    "pyautogui": PyAutoGuiBot,
    "itchat": ItchatBot,
    "vcf": VcfExporter,
}

def create(type: str, **kwargs) -> WechatBot:
    cls = BOTS.get(type, VcfExporter)
    return cls(**kwargs)
