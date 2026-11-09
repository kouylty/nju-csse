"""Validate, sanitize and store pictures; authorize reads through product references."""

import io
import secrets
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.clock import now, timestamp
from app.db import read_transaction, write_transaction
from app.domain import Role
from app.errors import BusinessError
from app.repositories import files, logs

FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


class FileService:
    def __init__(
        self, conn, directory, *, clock=now, max_bytes=5 * 1024 * 1024, max_pixels=20_000_000
    ):
        self.conn = conn
        self.directory = Path(directory)
        self.clock = clock
        self.max_bytes = max_bytes
        self.max_pixels = max_pixels

    def upload(self, actor, stream):
        raw = stream.read(self.max_bytes + 1)
        if len(raw) > self.max_bytes:
            raise BusinessError("IMAGE_TOO_LARGE", "每张图片不得超过 5 MiB。")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as original:
                    format_name = original.format
                    if format_name not in FORMATS:
                        raise BusinessError("INVALID_IMAGE", "请选择 JPG、PNG 或 WebP 图片。")
                    width, height = original.size
                    if width * height > self.max_pixels:
                        raise BusinessError("IMAGE_TOO_LARGE", "图片像素总数不得超过两千万。")
                    original.verify()
                with (
                    Image.open(io.BytesIO(raw)) as original,
                    ImageOps.exif_transpose(original) as oriented,
                ):
                    mode = (
                        "RGBA"
                        if oriented.mode in ("RGBA", "LA", "P") and format_name != "JPEG"
                        else "RGB"
                    )
                    with oriented.convert(mode) as image:
                        image.info.clear()
                        width, height = image.size
                        output = io.BytesIO()
                        image.save(output, format=format_name)
        except (
            UnidentifiedImageError,
            SyntaxError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise BusinessError("INVALID_IMAGE", "图片无法读取，请选择完整的有效图片。") from None
        content = output.getvalue()
        if len(content) > self.max_bytes:
            raise BusinessError("IMAGE_TOO_LARGE", "处理后的图片超过大小限制，请缩小图片。")
        mime, extension = FORMATS[format_name]
        key = secrets.token_hex(24) + extension
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / key
        created = False
        try:
            with path.open("xb") as target:
                created = True
                target.write(content)
            with write_transaction(self.conn):
                file_id = files.insert(
                    self.conn,
                    owner_id=actor.id,
                    storage_key=key,
                    content_type=mime,
                    size_bytes=len(content),
                    width=width,
                    height=height,
                    created_at=timestamp(self.clock()),
                )
        except BaseException:
            if created:
                path.unlink(missing_ok=True)
            raise
        return {
            "id": file_id,
            "url": f"/api/files/{file_id}",
            "content_type": mime,
            "width": width,
            "height": height,
            "size_bytes": len(content),
        }

    def open_for(self, actor, file_id):
        # Keep assigned-case authorization and its audit event in one serialized operation.
        transaction = (
            write_transaction
            if actor is not None and actor.role == Role.ADMIN and not self.conn.in_transaction
            else read_transaction
        )
        with transaction(self.conn):
            return self._authorized_path(actor, file_id)

    def _authorized_path(self, actor, file_id):
        row = files.get_by_id(self.conn, file_id)
        case = files.case_access(self.conn, file_id, actor.id) if actor else None
        allowed = row is not None and (
            (actor is not None and actor.id == row["owner_id"])
            or case is not None
            or (actor is not None and files.order_visible(self.conn, file_id, actor.id))
            or files.publicly_visible(self.conn, file_id)
            or (
                actor is not None
                and actor.role == Role.ADMIN
                and files.reviewable(self.conn, file_id)
            )
        )
        if not allowed:
            raise BusinessError("NOT_FOUND", "图片不存在或当前不可访问。")
        path = (self.directory / row["storage_key"]).resolve()
        if path.parent != self.directory.resolve() or not path.is_file():
            raise BusinessError("NOT_FOUND", "图片不存在。")
        if case is not None and actor.role == Role.ADMIN:
            logs.append(
                self.conn,
                actor_kind="USER",
                actor_id=actor.id,
                action="CASE_FILE_VIEWED",
                object_type="CASE",
                object_id=case["id"],
                before={},
                after={"file_id": file_id},
                at=timestamp(self.clock()),
            )
        return path, row["content_type"]
