"""열린국회정보 OPEN API 클라이언트 - 발의/처리 법률안 조회."""
import httpx

from app.config import (
    ASSEMBLY_AGE,
    ASSEMBLY_BASE,
    ASSEMBLY_BILL_SERVICE,
    ASSEMBLY_KEY,
    REQUEST_TIMEOUT,
)


class AssemblyError(RuntimeError):
    pass


def _unwrap(payload: dict, service: str) -> tuple[list[dict], int]:
    """열린국회정보 응답 봉투에서 row 리스트와 전체건수를 추출한다."""
    # 오류(데이터 없음 등)는 최상위 RESULT로 내려온다.
    if "RESULT" in payload:
        code = payload["RESULT"].get("CODE", "")
        if not code.startswith("INFO-00"):
            raise AssemblyError(payload["RESULT"].get("MESSAGE", code))
        return [], 0

    blocks = payload.get(service)
    if not blocks:
        raise AssemblyError(f"예상치 못한 응답 형식: 최상위 키 {list(payload)}")

    total, rows = 0, []
    for block in blocks:
        if "head" in block:
            for item in block["head"]:
                if "list_total_count" in item:
                    total = item["list_total_count"]
                if "RESULT" in item and not item["RESULT"]["CODE"].startswith("INFO-00"):
                    raise AssemblyError(item["RESULT"]["MESSAGE"])
        if "row" in block:
            rows = block["row"]
    return rows, total


def fetch_bills(age: str | None = None, p_index: int = 1, p_size: int = 100,
                proc_result: str | None = None) -> tuple[list[dict], int]:
    """국회 의안(법률안) 목록을 조회한다.

    proc_result 를 주면 처리결과(PROC_RESULT_CD)로 서버에서 필터링한다
    (예: '원안가결'). 최근 의안은 대부분 계류 상태라, 가결 의안만 보려면
    서버 필터가 필요하다(표본 안에서 클라이언트 필터로는 거의 안 잡힘).
    """
    if not ASSEMBLY_KEY:
        raise AssemblyError("ASSEMBLY_KEY가 설정되지 않았습니다 (.env 확인).")

    params = {
        "KEY": ASSEMBLY_KEY,
        "Type": "json",
        "pIndex": p_index,
        "pSize": p_size,
        "AGE": age or ASSEMBLY_AGE,
    }
    if proc_result:
        params["PROC_RESULT_CD"] = proc_result
    url = f"{ASSEMBLY_BASE}/{ASSEMBLY_BILL_SERVICE}"
    try:
        resp = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AssemblyError(f"국회 API 요청 실패: {exc}") from exc

    return _unwrap(resp.json(), ASSEMBLY_BILL_SERVICE)


def is_passed(bill: dict) -> bool:
    """처리결과가 가결(원안/수정)인 법률안인지 판단한다."""
    result = (bill.get("PROC_RESULT") or bill.get("PROC_RESULT_CD") or "")
    return "가결" in result


def normalize_bill(bill: dict) -> dict:
    """대시보드에서 쓰기 쉬운 형태로 핵심 필드만 추린다."""
    return {
        "bill_id": bill.get("BILL_ID", ""),
        "bill_no": bill.get("BILL_NO", ""),
        "name": bill.get("BILL_NAME", ""),
        "committee": bill.get("CURR_COMMITTEE") or "",
        "propose_dt": bill.get("PROPOSE_DT") or "",
        "proc_result": bill.get("PROC_RESULT") or bill.get("PROC_RESULT_CD") or "",
        "proc_dt": bill.get("PROC_DT") or "",
        "link": bill.get("LINK_URL") or bill.get("DETAIL_LINK") or "",
        "passed": is_passed(bill),
    }
