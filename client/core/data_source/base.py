"""数据源抽象接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class Contact:
    """联系人"""
    company: str = ""
    name: str = ""
    phone: str = ""
    extra: dict = field(default_factory=dict)

class DataSource(ABC):
    @abstractmethod
    def fetch(self, keyword: str = "", **kwargs) -> list[Contact]:
        """返回联系人列表"""
        ...

    @abstractmethod
    def name(self) -> str:
        """数据源显示名"""
        ...
