"""국가법령정보센터 OPEN API 클라이언트 - 자치법규(조례) 및 법령 본문 조회."""
import re
import xml.etree.ElementTree as ET

import httpx

from app.config import GYEONGGI_ORG, LAW_BASE, LAW_LINK_TARGET, LAW_OC, REQUEST_TIMEOUT

# 인증·IP 미등록 등 '전역 실패' 메시지 단서 (개별 미발견과 구분)
_AUTH_HINTS = ("검증", "IP", "등록")

# law.go.kr 자치법규 목록의 한글 태그 → 표준 키 매핑
_FIELD_MAP = {
    "자치법규명": "name",
    "자치법규ID": "ordin_id",
    "지자체기관명": "org",
    "제개정구분명": "revision",
    "공포일자": "promulgated",
    "자치법규상세링크": "link",
    "자치법규종류": "kind",
}


class LawError(RuntimeError):
    pass


# XML 표준 엔티티(&amp; &lt; &gt; &quot; &apos; &#..;)가 아닌 '&'를 escape 한다.
# 법령센터가 검색어를 응답에 그대로 echo 하면서 가운뎃점(·)을 &middot; 같은
# HTML 전용(=XML 비표준) 엔티티로 돌려줘 파싱이 깨지는 것을 막는다.
_STRAY_AMP = re.compile(r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)")


def _fromstring(xml_text: str) -> ET.Element:
    return ET.fromstring(_STRAY_AMP.sub("&amp;", xml_text))


def _response_error(root: ET.Element) -> str | None:
    """오류 응답(<Response><result>..</result><msg>..</msg>)이면 메시지를 돌려준다."""
    if root.tag == "Response":
        msg = f'{root.findtext("result", "")} {root.findtext("msg", "")}'.strip()
        return msg or "법령센터 인증/요청 오류"
    return None


def _extract_ordin_records(root: ET.Element) -> list[dict]:
    """XML 트리에서 자치법규 레코드(_FIELD_MAP 기준)를 뽑아낸다. (오류 판정 제외)"""
    records = []
    # 반복 요소는 <law>. 안전하게 자식 중 하위요소가 있는 것을 순회.
    items = root.findall("law") or [c for c in root if len(c)]
    for item in items:
        rec = {}
        for child in item:
            key = _FIELD_MAP.get(child.tag)
            if key:
                rec[key] = (child.text or "").strip()
        if rec.get("name"):
            link = rec.get("link", "")
            if link.startswith("/"):
                rec["link"] = "https://www.law.go.kr" + link
            records.append(rec)
    return records


def _parse_records(xml_text: str) -> list[dict]:
    """LawSearch XML에서 자치법규 레코드를 추출한다 (오류 응답이면 LawError)."""
    try:
        root = _fromstring(xml_text)
    except ET.ParseError as exc:
        raise LawError(f"법령센터 응답 파싱 실패: {exc}") from exc

    err = _response_error(root)
    if err:
        raise LawError(err)
    return _extract_ordin_records(root)


def search_ordinances(query: str, region: str = GYEONGGI_ORG, display: int = 50) -> list[dict]:
    """키워드로 자치법규를 검색하고 특정 지자체(기본: 경기도)만 필터링한다."""
    params = {
        "OC": LAW_OC,
        "target": "ordin",
        "type": "XML",
        "query": query,
        "display": min(display, 100),
        "page": 1,
    }
    try:
        resp = httpx.get(f"{LAW_BASE}/lawSearch.do", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise LawError(f"법령센터 요청 실패: {exc}") from exc

    records = _parse_records(resp.text)
    if region:
        records = [r for r in records if region in r.get("org", "")]
    return records


def get_law_text(law_name: str) -> str:
    """법령명으로 현행 법령 본문을 받아 공백 정규화한 평문으로 돌려준다.

    법령명이 해결되지 않으면 "" 를 돌려주고(개별 미발견), 인증·IP 오류처럼
    전역 실패는 LawError 로 전파한다.

    본문은 '위임조항' 보조 분석용이므로, 타임아웃·일시적 네트워크/파싱 오류는
    개별 미확인("")으로 처리한다. 한 건의 지연이 전체 분석을 중단시키지 않게 한다.
    """
    if not law_name:
        return ""
    params = {"OC": LAW_OC, "target": "law", "type": "XML", "LM": law_name}
    try:
        resp = httpx.get(f"{LAW_BASE}/lawService.do", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = _fromstring(resp.text)
    except (httpx.HTTPError, ET.ParseError):
        return ""  # 본문 미확인(타임아웃·일시 오류 등) → 위임조항 '확인불가'

    err = _response_error(root)
    if err:
        if any(h in err for h in _AUTH_HINTS):
            raise LawError(err)
        return ""  # 법령명 미해결 등 개별 사유
    return re.sub(r"\s+", " ", "".join(root.itertext())).strip()


def search_linked_ordinances(law_name: str, region: str = GYEONGGI_ORG) -> list[dict]:
    """법령에 '공식 연계된' 자치법규를 조회한다 (target=lnkLs, 법령명으로 검색).

    법제처가 직접 연결한 권위 있는 매핑이라 키워드 추정보다 정확하다.
    이 응답에는 지자체기관명이 없어 자치법규명에 region 포함 여부로 필터링한다.
    연계는 '보조 신호'이므로 실패하면 빈 목록을 돌려 본 흐름을 유지한다.
    """
    if not law_name or not LAW_LINK_TARGET:
        return []
    params = {"OC": LAW_OC, "target": LAW_LINK_TARGET, "type": "XML",
              "query": law_name, "display": 100}
    try:
        resp = httpx.get(f"{LAW_BASE}/lawSearch.do", params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = _fromstring(resp.text)
    except (httpx.HTTPError, ET.ParseError):
        return []
    if _response_error(root):
        return []

    merged: dict[str, dict] = {}
    for rec in _extract_ordin_records(root):
        if region and region not in (rec.get("org", "") + rec.get("name", "")):
            continue
        rec["linked"] = True
        merged[rec.get("ordin_id") or rec["name"]] = rec
    return list(merged.values())
