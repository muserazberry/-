"""국민신문고 민원 질의응답 / 국민생각함 국민제안 게시판 수집기 (HTML 파싱).

전국 단위 게시판이라 소관기관을 메타로 함께 보관해 분류에 쓴다.
RSS·공공데이터 API 없이 epeople.go.kr 목록 HTML을 직접 파싱한다.
컬럼: [번호, 제목, 소관기관, 날짜, (제안: 처리상태) …].
사이트 마크업이 바뀌면 아래 정규식 조정이 필요하다.
"""
import re

import httpx

from app.config import (EPEOPLE_IDEA_URL, EPEOPLE_LIMIT, EPEOPLE_MINWON_URL,
                        REQUEST_TIMEOUT)

_TBODY = re.compile(r"<tbody[^>]*>(.*?)</tbody>", re.S)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_HEADERS = {"User-Agent": "Mozilla/5.0"}
_MAX_PAGES = 10  # 폭주 방지 상한 (페이지당 약 10건)


class EpeopleError(RuntimeError):
    pass


def _text(fragment: str) -> str:
    """셀 HTML → 태그 제거·공백 정리한 순수 텍스트."""
    return _WS.sub(" ", _TAG.sub(" ", fragment)).strip()


def parse(html_text: str, with_status: bool = False) -> list[dict]:
    """목록 HTML → [{title, agency, date, status?}]."""
    m = _TBODY.search(html_text)
    if not m:
        return []
    items = []
    for row in _ROW.findall(m.group(1)):
        cells = [_text(td) for td in _TD.findall(row)]
        if len(cells) < 4 or not cells[1]:
            continue
        item = {"title": cells[1], "agency": cells[2], "date": cells[3]}
        if with_status and len(cells) > 4:
            item["status"] = cells[4]
        items.append(item)
    return items


def _fetch(url: str, limit: int, with_status: bool) -> list[dict]:
    out: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        try:
            resp = httpx.get(url, params={"pageIndex": page}, headers=_HEADERS,
                             timeout=REQUEST_TIMEOUT, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EpeopleError(f"국민신문고 요청 실패: {exc}") from exc
        rows = parse(resp.text, with_status)
        if not rows:
            break
        out.extend(rows)
        if len(out) >= limit:
            break
    return out[:limit]


def fetch_minwon(limit: int = EPEOPLE_LIMIT) -> list[dict]:
    """민원 질의응답·답변원문 목록."""
    return _fetch(EPEOPLE_MINWON_URL, limit, with_status=False)


def fetch_ideas(limit: int = EPEOPLE_LIMIT) -> list[dict]:
    """국민생각함 국민제안 목록 (처리상태 포함)."""
    return _fetch(EPEOPLE_IDEA_URL, limit, with_status=True)
