"""경기도의회 입법예고(조례안) 게시판 수집기.

RSS·공공데이터 API가 없어 ggc.go.kr 입법예고 게시판 목록 HTML을 직접 파싱한다.
각 행(<tr>)에서 제목·상세링크·공고일·의견마감일을 뽑는다.
사이트 마크업이 바뀌면 아래 정규식(_LINK 등) 조정이 필요하다.
"""
import html
import re

import httpx

from app.config import COUNCIL_BASE, COUNCIL_LIMIT, COUNCIL_SITE, REQUEST_TIMEOUT

_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
_LINK = re.compile(r'href="(/site/main/board/lgslt/\d+[^"]*)">(.*?)</a>', re.S)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

_MAX_PAGES = 10  # 폭주 방지 상한 (페이지당 약 10건)


class CouncilError(RuntimeError):
    pass


def parse(html_text: str) -> list[dict]:
    """게시판 목록 HTML → [{title, link, start, end}]."""
    items = []
    for row in _ROW.findall(html_text):
        m = _LINK.search(row)
        if not m:
            continue
        title = html.unescape(m.group(2)).strip()
        title = title.splitlines()[0].strip() if title else ""
        if not title:
            continue
        dates = _DATE.findall(row)
        items.append({
            "title": title,
            "link": COUNCIL_SITE + html.unescape(m.group(1)),
            "start": dates[0] if dates else "",        # 공고일
            "end": dates[1] if len(dates) > 1 else "",  # 의견마감일
        })
    return items


def fetch_preannouncements(limit: int = COUNCIL_LIMIT) -> list[dict]:
    """입법예고 목록을 limit 건까지 페이지를 넘기며 모은다."""
    out: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        params = {"cp": page, "listType": "list", "bcId": "lgslt"}
        try:
            resp = httpx.get(COUNCIL_BASE, params=params,
                             timeout=REQUEST_TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise CouncilError(f"의회 입법예고 요청 실패: {exc}") from exc
        rows = parse(resp.text)
        if not rows:
            break
        out.extend(rows)
        if len(out) >= limit:
            break
    return out[:limit]
