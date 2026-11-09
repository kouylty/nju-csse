"""Product input and publication rules, shared by all product entry points."""

from app.domain import PRODUCT_CATEGORIES
from app.errors import BusinessError

MAX_MONEY = 2**53 - 1
FIELDS = {
    "title",
    "description",
    "category",
    "type",
    "price_cents",
    "available_stock",
    "allow_post",
    "allow_meet",
    "free_shipping",
    "postage_cents",
    "meeting_description",
    "image_ids",
}
REVIEW_FIELDS = FIELDS - {"price_cents", "postage_cents", "free_shipping", "available_stock"}
DEFAULTS = {
    "title": "",
    "description": "",
    "category": "",
    "type": "GOODS",
    "price_cents": None,
    "available_stock": 1,
    "allow_post": False,
    "allow_meet": True,
    "free_shipping": True,
    "postage_cents": 0,
    "meeting_description": "",
    "image_ids": [],
}


def invalid(message, field):
    raise BusinessError("INVALID_INPUT", message, {"field": field})


def integer(value, field, *, minimum=0, maximum=MAX_MONEY):
    if type(value) is not int or not minimum <= value <= maximum:
        invalid(f"{field} 须为 {minimum} 至 {maximum} 之间的整数。", field)
    return value


def text(value, field, maximum=1000, *, required=False):
    if not isinstance(value, str) or len(value) > maximum:
        invalid(f"{field} 须为不超过 {maximum} 个字符的文本。", field)
    result = value.strip()
    if required and not result:
        invalid("请填写必要的说明。", field)
    return result


def merge_product(current, patch):
    if not isinstance(patch, dict) or patch.keys() - FIELDS:
        invalid("包含无法编辑的商品字段。", "product")
    result = {key: current[key] for key in FIELDS}
    result.update(patch)
    for field, size in [("title", 60), ("description", 3000), ("meeting_description", 500)]:
        result[field] = text(result[field], field, size)
    if result["category"] not in ("", *PRODUCT_CATEGORIES):
        invalid("请选择有效分类。", "category")
    if result["type"] not in ("GOODS", "SERVICE"):
        invalid("请选择物品或服务。", "type")
    if result["price_cents"] is not None:
        integer(result["price_cents"], "price_cents", minimum=1)
    integer(result["available_stock"], "available_stock", maximum=2**31 - 1)
    integer(result["postage_cents"], "postage_cents")
    for field in ["allow_post", "allow_meet", "free_shipping"]:
        if type(result[field]) is not bool:
            invalid("交付选项须为布尔值。", field)
    images = result["image_ids"]
    if not isinstance(images, list) or len(images) > 6:
        invalid("每件商品最多关联六张图片。", "image_ids")
    for image_id in images:
        integer(image_id, "image_ids", minimum=1)
    if len(images) != len(set(images)):
        invalid("商品图片不能重复。", "image_ids")
    if result["type"] == "SERVICE" and (
        result["allow_post"] or result["allow_meet"] or result["postage_cents"]
    ):
        invalid("服务使用服务交付，邮费应为零。", "type")
    return result


def require_complete(data, *, positive_stock=True):
    for field in ["title", "description", "category"]:
        if not data[field]:
            invalid("请完整填写商品资料。", field)
    if data["price_cents"] is None or not data["image_ids"]:
        invalid(
            "请填写价格并至少添加一张图片。",
            "price_cents" if data["price_cents"] is None else "image_ids",
        )
    if positive_stock and data["available_stock"] < 1:
        invalid("提交审核时库存须为正整数。", "available_stock")
    if data["type"] == "GOODS":
        if not data["allow_post"] and not data["allow_meet"]:
            invalid("请选择至少一种交付方式。", "allow_meet")
        if data["allow_meet"] and not data["meeting_description"]:
            invalid("请说明当面交付方式。", "meeting_description")
        if data["allow_post"]:
            if data["free_shipping"] != (data["postage_cents"] == 0):
                invalid("包邮时邮费为零，不包邮时邮费须大于零。", "postage_cents")
        elif data["postage_cents"] != 0:
            invalid("当面交付的邮费应为零。", "postage_cents")
