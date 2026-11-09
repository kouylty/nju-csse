"""Shared identities and authentication results, independent of HTTP and SQL."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.errors import BusinessError


class Role(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class ProductStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    OFFLINE = "OFFLINE"
    BLOCKED = "BLOCKED"


class OrderStatus(StrEnum):
    UNPAID = "UNPAID"
    WAITING_DELIVERY = "WAITING_DELIVERY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class PlacementResult:
    order_id: int
    created: bool


PRODUCT_CATEGORIES = ("数码电子", "书籍文具", "生活好物", "服饰配件", "虚拟商品", "技能服务")


@dataclass(frozen=True)
class Actor:
    id: int
    username: str
    role: Role

    def require_admin(self) -> None:
        if self.role != Role.ADMIN:
            raise BusinessError("FORBIDDEN", "此操作需要管理员权限。")

    def to_dict(self) -> dict:
        return {"id": self.id, "username": self.username, "role": self.role.value}


@dataclass(frozen=True)
class AuthenticatedSession:
    actor: Actor
    expires_at: datetime


@dataclass(frozen=True)
class LoginResult:
    session: AuthenticatedSession
    token: str
