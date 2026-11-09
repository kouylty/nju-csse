"""Small input rules shared by services and transport adapters."""

import unicodedata

from app.errors import BusinessError


def username(value: object) -> str:
    if not isinstance(value, str):
        raise BusinessError("INVALID_INPUT", "请填写用户名。", {"field": "username"})
    result = unicodedata.normalize("NFKC", value).strip()
    if not 3 <= len(result) <= 32 or not all(c.isalnum() or c in "._-" for c in result):
        raise BusinessError(
            "INVALID_INPUT", "用户名须为 3—32 个字母、数字或 ._- 字符。", {"field": "username"}
        )
    return result


def username_key(value: str) -> str:
    return value.casefold()


def password(value: object) -> str:
    if not isinstance(value, str) or not 8 <= len(value) <= 128 or value.isspace():
        raise BusinessError(
            "INVALID_INPUT", "密码须为 8—128 个字符，且不能全部为空白。", {"field": "password"}
        )
    return value


def pagination(limit: object, offset: object) -> tuple[int, int]:
    try:
        if isinstance(limit, bool) or isinstance(offset, bool):
            raise ValueError
        if not str(limit).isascii() or not str(limit).isdecimal():
            raise ValueError
        if not str(offset).isascii() or not str(offset).isdecimal():
            raise ValueError
        size, start = int(limit), int(offset)
        if not 1 <= size <= 100 or not 0 <= start <= 2**31 - 1:
            raise ValueError
    except (TypeError, ValueError):
        raise BusinessError("INVALID_INPUT", "limit 须为 1—100，offset 须为非负整数。") from None
    return size, start
