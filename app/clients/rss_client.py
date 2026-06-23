"""범용 RSS/Atom 클라이언트 - 정책·보도자료 피드를 신호 항목으로 수집."""
import xml.etree.ElementTree as ET

import httpx

from app.config import REQUEST_TIMEOUT


class RSSError(RuntimeError):
    pass


def _strip_ns(root: ET.Element) -> None:
    """{namespace}tag → tag 로 정규화해 태그 탐색을 단순화한다."""
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def _link_of(item: ET.Element) -> str:
    """RSS는 <link>텍스트, Atom은 <link href=..> 형태를 모두 처리."""
    link = item.find("link")
    if link is not None:
        return (link.text or link.get("href") or "").strip()
    return ""


def parse(content: bytes, source_hint: str = "") -> list[dict]:
    """RSS 2.0 / Atom 본문을 항목 리스트로 변환한다."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise RSSError(f"RSS 파싱 실패: {exc}") from exc
    _strip_ns(root)

    source = root.findtext(".//channel/title") or root.findtext("title") or source_hint
    nodes = list(root.iter("item")) or list(root.iter("entry"))
    items = []
    for node in nodes:
        title = (node.findtext("title") or "").strip()
        if not title:
            continue
        items.append({
            "source": (source or "RSS").strip(),
            "title": title,
            "summary": (node.findtext("description") or node.findtext("summary") or "").strip(),
            "link": _link_of(node),
            "date": (node.findtext("pubDate") or node.findtext("updated") or "").strip(),
        })
    return items


def fetch(url: str, limit: int = 40) -> list[dict]:
    """피드 URL을 받아 항목을 최대 limit개 수집한다."""
    try:
        resp = httpx.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RSSError(f"RSS 요청 실패({url}): {exc}") from exc
    return parse(resp.content, source_hint=url)[:limit]
