"""열린국회정보 OPEN API 클라이언트 - 국회의원/국회도서관 세미나 일정 조회.

발의법률안 서비스(assembly_client)와 동일한 응답 봉투를 쓰므로 _unwrap/AssemblyError를
재사용한다. 세미나 서비스의 컬럼명은 서비스마다 표기가 달라 흔한 후보를 자동 인식한다.
"""
import httpx

from app.clients.assembly_client import AssemblyError, _unwrap
from app.config import (
    ASSEMBLY_BASE,
    ASSEMBLY_KEY,
    ASSEMBLY_SEMINAR_LIMIT,
    ASSEMBLY_SEMINAR_SERVICE,
    REQUEST_TIMEOUT,
)


def _pick(row: dict, *subs: str) -> str:
    """컬럼명에 후보 문자열이 포함된 첫 값을 반환 (대소문자 무시)."""
    for sub in subs:
        for key, val in row.items():
            if sub in key.upper() and val:
                return str(val).strip()
    return ""


def normalize_seminar(row: dict) -> dict:
    """세미나 한 건을 대시보드용 핵심 필드로 정리한다.

    서비스별 컬럼 표기가 달라 흔한 후보를 우선순위로 자동 인식한다.
    """
    return {
        "title": _pick(row, "TITLE", "SUBJECT", "SMINR", "SJ", "NM"),
        "date": _pick(row, "DATE", "_DE", "_DT", "YMD", "TM"),
        "host": _pick(row, "HOST", "SPONSOR", "MAINTART", "ORG", "DEPT"),
        "place": _pick(row, "PLACE", "PLC", "LOC", "AREA"),
        "link": _pick(row, "LINK", "URL"),
    }


def fetch_seminars(limit: int = ASSEMBLY_SEMINAR_LIMIT) -> list[dict]:
    """세미나 일정 목록을 조회해 정규화된 리스트로 반환한다."""
    if not ASSEMBLY_KEY:
        raise AssemblyError("ASSEMBLY_KEY가 설정되지 않았습니다 (.env 확인).")
    if not ASSEMBLY_SEMINAR_SERVICE:
        raise AssemblyError(
            "ASSEMBLY_SEMINAR_SERVICE가 비어 있습니다. 열린국회정보 대시보드에서 "
            "'세미나 일정' 서비스 ID를 확인해 .env에 입력하세요."
        )

    params = {
        "KEY": ASSEMBLY_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": min(limit, 100),
    }
    url = f"{ASSEMBLY_BASE}/{ASSEMBLY_SEMINAR_SERVICE}"
    try:
        resp = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AssemblyError(f"세미나 API 요청 실패: {exc}") from exc

    rows, _ = _unwrap(resp.json(), ASSEMBLY_SEMINAR_SERVICE)
    return [normalize_seminar(r) for r in rows[:limit]]
