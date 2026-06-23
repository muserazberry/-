"""정부입법지원센터 입법예고 목록 조회 클라이언트.

입법예고는 '통과 전' 단계라, 미리 경기도 조례 영향을 보면 선제 대응이 가능하다.
법제처 동일 OC(이메일 ID) 인증을 쓰며 XML을 돌려준다.
"""
import xml.etree.ElementTree as ET

import httpx

from app.config import LAWMAKING_BASE, LAWMAKING_LIMIT, LAWMAKING_OC, REQUEST_TIMEOUT

# 입법예고 XML 태그 → 표준 키 (표기 변형까지 흡수)
_FIELD_MAP = {
    "lsNm": "name",         # 법령안명
    "mppNm": "name",
    "billNm": "name",
    "asndDptNm": "ministry",  # 소관부처
    "deptNm": "ministry",
    "stYd": "start",        # 예고 시작일
    "ppStYd": "start",
    "edYd": "end",          # 예고 종료일
    "ppEdYd": "end",
    "lmPpDtlUrl": "link",   # 상세 링크
    "dtlUrl": "link",
}


class LawmakingError(RuntimeError):
    pass


def _records(root: ET.Element) -> list[dict]:
    """반복 항목에서 입법예고 레코드를 추출한다. (태그명 변형에 관대)"""
    items = root.findall(".//ogLmPp") or root.findall(".//item") or [c for c in root if len(c)]
    out = []
    for item in items:
        rec: dict[str, str] = {}
        for child in item:
            key = _FIELD_MAP.get(child.tag)
            if key and not rec.get(key):
                rec[key] = (child.text or "").strip()
        if rec.get("name"):
            out.append(rec)
    return out


def fetch_preannouncements(limit: int = LAWMAKING_LIMIT) -> list[dict]:
    """현재 입법예고 목록을 표준 레코드로 돌려준다."""
    if not LAWMAKING_OC:
        raise LawmakingError("LAWMAKING_OC(또는 LAW_OC)가 설정되지 않았습니다.")
    params = {"OC": LAWMAKING_OC, "display": min(limit, 100), "page": 1}
    try:
        # 목록은 확장자 형식(/ogLmPp.xml). www→opinion 리다이렉트도 대비해 따라간다.
        resp = httpx.get(f"{LAWMAKING_BASE}/ogLmPp.xml", params=params,
                         timeout=REQUEST_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except httpx.HTTPError as exc:
        raise LawmakingError(f"입법예고 요청 실패: {exc}") from exc
    except ET.ParseError as exc:
        raise LawmakingError(f"입법예고 응답 파싱 실패: {exc}") from exc

    _raise_if_error(root)
    return _records(root)


# 인증·요청 오류 응답 형태와 안내 메시지
#  - 신형: <result><retMsg>401</retMsg></result>
#  - 구형: <Response><result>..</result><msg>..</msg></Response>
_RETMSG_HINT = {
    "401": "OC 인증 실패 - 정부입법지원센터(opinion.lawmaking.go.kr)에서 "
           "OPEN API 사용 신청(정보공개 계정)을 해야 합니다.",
    "404": "입법예고 목록을 찾을 수 없습니다 (엔드포인트 확인 필요).",
}


def _raise_if_error(root: ET.Element) -> None:
    if root.tag == "result":
        code = (root.findtext("retMsg", "") or "").strip()
        hint = _RETMSG_HINT.get(code, "입법예고 인증/요청 오류")
        raise LawmakingError(f"{code}: {hint}" if code else hint)
    if root.tag == "Response":
        msg = f'{root.findtext("result", "")} {root.findtext("msg", "")}'.strip()
        raise LawmakingError(msg or "입법예고 인증/요청 오류")
