from html import unescape
from html.parser import HTMLParser


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"br", "p", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li"}:
            self.parts.append("\n")


def html_to_plain_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    parser = _HTMLTextExtractor()
    parser.feed(unescape(text))
    parser.close()

    normalized = "".join(parser.parts)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.strip() for line in normalized.split("\n") if line.strip())
