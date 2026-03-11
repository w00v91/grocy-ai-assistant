from __future__ import annotations

from base64 import b64encode
from urllib.parse import ParseResult, urljoin, urlparse

from grocy_ai_assistant.config.settings import Settings

_LOOPBACK_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "homeassistant"}


def maybe_encode_product_picture_path(path: str) -> str:
    if "/productpictures/" not in path:
        return path

    prefix, _, suffix = path.rpartition("/")
    if not suffix or "." not in suffix:
        return path

    encoded_picture_name = b64encode(suffix.encode("utf-8")).decode("ascii")
    return f"{prefix}/{encoded_picture_name}"


def build_product_picture_url(raw_picture_url: str, settings: Settings) -> str:
    picture_value = (raw_picture_url or "").strip()
    if not picture_value:
        return ""

    if picture_value.startswith("data:"):
        return picture_value

    parsed_grocy_base = urlparse(settings.grocy_base_url.rstrip("/"))
    grocy_base_url = parsed_grocy_base.geturl().rstrip("/")

    if picture_value.startswith(("http://", "https://")):
        parsed_picture = urlparse(picture_value)
        if parsed_picture.hostname in _LOOPBACK_HOSTNAMES:
            return ParseResult(
                scheme=parsed_grocy_base.scheme or parsed_picture.scheme,
                netloc=parsed_grocy_base.netloc or parsed_picture.netloc,
                path=maybe_encode_product_picture_path(parsed_picture.path),
                params=parsed_picture.params,
                query=parsed_picture.query,
                fragment=parsed_picture.fragment,
            ).geturl()
        return picture_value

    if "/" not in picture_value:
        encoded_picture_name = b64encode(picture_value.encode("utf-8")).decode("ascii")
        picture_value = f"files/productpictures/{encoded_picture_name}"

    picture_value = maybe_encode_product_picture_path(picture_value)

    if picture_value.startswith("/"):
        return urljoin(f"{grocy_base_url}/", picture_value)

    return f"{grocy_base_url}/{picture_value.lstrip('/')}"
