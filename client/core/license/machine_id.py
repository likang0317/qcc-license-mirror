"""设备唯一标识（device_id）采集"""
import uuid
import hashlib


def get_device_id() -> str:
    """采集主网卡 MAC → SHA256 → 取前 32 位作为设备 ID。

    纯标准库，无依赖。
    换硬盘/加内存/改主机名/重装系统 → 不影响。
    换 USB 无线网卡 → 会变（管理员解绑重绑解决）。
    """
    mac = uuid.getnode()
    raw = str(mac).encode()
    return hashlib.sha256(raw).hexdigest()[:32]


if __name__ == "__main__":
    print("device_id =", get_device_id())
