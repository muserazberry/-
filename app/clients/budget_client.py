"""세출예산 CSV 로더: 사업명·금액·전년예산을 읽어 신규/대규모/증액을 판정한다.

경기도청·경기도교육청 예산서(엑셀)를 CSV로 저장하거나 경기데이터드림 CSV를
그대로 넣으면 된다. 컬럼명은 흔한 한글 표기를 자동 인식한다.
"""
import csv
import re

# 표준 필드 → 인식할 CSV 헤더 후보 (부분 일치, 앞에서부터 우선)
_COLUMNS = {
    "name": ["세부사업명", "단위사업명", "정책사업명", "사업명", "사업"],
    "dept": ["부서명", "실국명", "담당부서", "부서", "소관"],
    "amount": ["금년", "당해", "올해", "본예산", "예산액", "예산현액", "예산"],
    "prev": ["전년도", "전년", "지난해", "직전"],
    "is_new": ["신규여부", "신규", "구분"],
}


class BudgetError(RuntimeError):
    pass


def _num(value: str | None) -> float | None:
    """'1,234,000원' 같은 값에서 숫자만 뽑아 float 로. 못 뽑으면 None."""
    if not value:
        return None
    digits = re.sub(r"[^\d.]", "", value)
    return float(digits) if digits else None


def _pick(headers: list[str], candidates: list[str]) -> str | None:
    """헤더 목록에서 후보 표기를 포함하는 첫 컬럼명을 고른다."""
    for cand in candidates:
        for head in headers:
            if cand in head:
                return head
    return None


def _read_rows(path: str) -> tuple[list[dict], list[str]]:
    """CSV를 읽어 (행, 헤더) 반환. 한글 인코딩(utf-8-sig→cp949) 자동 대응."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            with open(path, encoding=enc, newline="") as fh:
                reader = csv.DictReader(fh)
                rows = [{(k or "").strip(): v for k, v in r.items()} for r in reader]
                return rows, [h.strip() for h in (reader.fieldnames or [])]
        except UnicodeDecodeError:
            continue
        except FileNotFoundError as exc:
            raise BudgetError(f"예산 파일을 찾을 수 없습니다: {path}") from exc
    raise BudgetError(f"예산 파일 인코딩을 해석할 수 없습니다: {path}")


def load(path: str, only_flagged: bool = True, top_n: int = 30,
         inc_pct: float = 0.5) -> list[dict]:
    """예산 사업 레코드 목록을 신규/대규모/증액 플래그와 함께 돌려준다."""
    rows, headers = _read_rows(path)
    col = {field: _pick(headers, cands) for field, cands in _COLUMNS.items()}
    if not col["name"]:
        raise BudgetError(f"사업명 컬럼을 찾지 못했습니다 (헤더: {headers}).")

    records = []
    for row in rows:
        name = (row.get(col["name"]) or "").strip()
        if not name:
            continue
        amount = _num(row.get(col["amount"])) if col["amount"] else None
        prev = _num(row.get(col["prev"])) if col["prev"] else None
        flag_text = (row.get(col["is_new"]) or "") if col["is_new"] else ""
        is_new = ("신규" in flag_text) or (prev == 0 and (amount or 0) > 0)
        delta_pct = ((amount - prev) / prev) if (prev and amount is not None) else None
        records.append({
            "name": name,
            "dept": (row.get(col["dept"]) or "").strip() if col["dept"] else "",
            "amount": amount,
            "prev": prev,
            "is_new": is_new,
            "delta_pct": delta_pct,
            "increased": delta_pct is not None and delta_pct >= inc_pct,
            "large": False,  # 아래에서 금액 상위 N개로 표시
        })

    # '대규모' = 금액 상위 N개 (단위를 모르므로 절대 임계 대신 순위 사용)
    amounts = sorted((r["amount"] for r in records if r["amount"] is not None), reverse=True)
    threshold = amounts[top_n - 1] if len(amounts) >= top_n else (amounts[-1] if amounts else None)
    if threshold is not None:
        for r in records:
            r["large"] = r["amount"] is not None and r["amount"] >= threshold

    for r in records:
        r["flagged"] = r["is_new"] or r["increased"] or r["large"]
    if only_flagged:
        records = [r for r in records if r["flagged"]]
    return records
