"""Typed checkout commands and canonical request identity."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass

from app.errors import BusinessError
from app.product_rules import integer


@dataclass(frozen=True)
class PlaceOrderInput:
    product_id: int
    quantity: int
    delivery_mode: str
    expected_unit_price_cents: int
    expected_postage_cents: int
    request_key: str

    @classmethod
    def parse(cls, data):
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise BusinessError(
                "INVALID_INPUT", "请按下单接口填写商品、数量、交付方式、确认金额和请求标识。"
            )
        return cls(**data)

    def __post_init__(self):
        integer(self.product_id, "product_id", minimum=1)
        integer(self.quantity, "quantity", minimum=1, maximum=2**31 - 1)
        integer(self.expected_unit_price_cents, "expected_unit_price_cents", minimum=1)
        integer(self.expected_postage_cents, "expected_postage_cents")
        if self.delivery_mode != "MEET":
            raise BusinessError("DELIVERY_UNAVAILABLE", "当前在线交易支持当面交付。")
        key = self.request_key
        if not isinstance(key, str) or re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", key) is None:
            raise BusinessError(
                "INVALID_INPUT", "request_key 须为 8—128 个字母、数字或 ._:- 字符。"
            )

    def fingerprint(self):
        data = asdict(self)
        del data["request_key"]
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()
