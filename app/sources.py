"""신호 출처 어댑터: 각 출처를 공통 signal 형식으로 변환한다.

signal = {"source", "title", "summary", "link", "date", "meta"}
새 단계(회의록·예산서 등)는 여기에 함수를 추가하면 추천 엔진이 그대로 처리한다.
"""
import re

from app import config
from app.analysis import delegation, relevance
from app.clients import (council_client, epeople_client, law_client,
                         lawmaking_client, rss_client, seminar_client)
from app.clients.assembly_client import AssemblyError, fetch_bills, normalize_bill
from app.clients.epeople_client import EpeopleError
from app.clients.rss_client import RSSError


def _bill_to_law_name(bill_name: str) -> str:
    """의안명에서 대상 법령명을 추정한다. (○○법 일부개정법률안 → ○○법)"""
    name = re.sub(r"\(.*?\)", "", bill_name or "").strip()
    name = re.sub(r"\s*(일부개정|전부개정|개정|폐지|제정)법률안$", "", name)
    name = re.sub(r"법률안$", "법률", name)
    name = re.sub(r"법안$", "법", name)
    return name.strip()


def _attach_delegation(sig: dict, bill_name: str, cache: dict[str, str]) -> None:
    """법령 본문을 받아 위임조항 유무·근거를 신호에 붙인다."""
    law_name = _bill_to_law_name(bill_name)
    if law_name not in cache:
        cache[law_name] = law_client.get_law_text(law_name)
    text = cache[law_name]
    if not text:
        sig["has_delegation"] = None  # 본문 미확인
        sig["meta"]["위임조항"] = "확인불가"
        return
    found = delegation.scan(text)
    sig["has_delegation"] = found["found"]
    sig["delegation_snippets"] = found["snippets"]
    sig["meta"]["위임조항"] = "있음" if found["found"] else "없음"


def _attach_linkage(sig: dict, bill_name: str, cache: dict[str, list[dict]]) -> None:
    """법제처 공식 연계 API로 이 법령과 연결된 경기도 자치법규를 신호에 붙인다."""
    law_name = _bill_to_law_name(bill_name)
    if law_name not in cache:
        cache[law_name] = law_client.search_linked_ordinances(law_name)
    linked = cache[law_name]
    if linked:
        sig["linked_ordinances"] = linked
        sig["meta"]["연계조례"] = f"{len(linked)}건"


def _enrich(sig: dict, law_target_name: str, text_cache: dict, link_cache: dict) -> None:
    """법령안 신호에 위임조항·공식 연계 정보를 붙인다 (국회·입법예고 공용)."""
    _attach_delegation(sig, law_target_name, text_cache)
    _attach_linkage(sig, law_target_name, link_cache)


def _assembly_signals(age=None, sample=100, only_passed=True, with_delegation=True, **_) -> list[dict]:
    """단계 ②③: 국회 (통과) 법률안. with_delegation 이면 본문 위임조항을 분석한다.

    only_passed 면 가결(원안·수정)만 서버에서 필터링해 받는다 — 최근 의안은
    대부분 계류라 클라이언트 필터로는 표본 안에서 가결 건이 거의 안 잡힌다.
    """
    size = min(sample, 100)
    if only_passed:
        merged: dict[str, dict] = {}
        for code in ("원안가결", "수정가결"):
            rows, _t = fetch_bills(age=age, p_size=size, proc_result=code)
            for r in rows:
                merged[r.get("BILL_ID") or r.get("BILL_NO")] = r
        # 최근 처리순으로 정렬해 표본 수만큼
        rows = sorted(merged.values(), key=lambda r: r.get("PROC_DT") or "", reverse=True)[:sample]
    else:
        rows, _t = fetch_bills(age=age, p_size=size)
    bills = [normalize_bill(r) for r in rows]

    signals, text_cache, link_cache = [], {}, {}
    for b in bills:
        sig = {
            "source": "국회 법률안",
            "title": b["name"],
            "summary": "",
            "link": b["link"],
            "date": b["proc_dt"] or b["propose_dt"],
            "meta": {"위원회": b["committee"], "처리결과": b["proc_result"]},
            "has_delegation": None,
        }
        if with_delegation:
            _enrich(sig, b["name"], text_cache, link_cache)
        signals.append(sig)
    return signals


def _lawmaking_signals(sample=100, with_delegation=True, **_) -> list[dict]:
    """단계 ②(선제): 정부 입법예고(통과 전). 미리 경기도 조례 영향을 본다."""
    rows = lawmaking_client.fetch_preannouncements(limit=min(sample, 100))
    signals, text_cache, link_cache = [], {}, {}
    for r in rows:
        period = " ~ ".join(x for x in (r.get("start"), r.get("end")) if x)
        sig = {
            "source": "입법예고",
            "title": r["name"],
            "summary": "",
            "link": r.get("link", ""),
            "date": r.get("start", ""),
            "meta": {"소관부처": r.get("ministry", ""), "예고기간": period},
            "has_delegation": None,
        }
        if with_delegation:
            _enrich(sig, r["name"], text_cache, link_cache)
        signals.append(sig)
    return signals


def _minwon_signals(sample=100, **_) -> list[dict]:
    """국민신문고 민원 질의응답(전국). 도민 수요 참고용 — 소관기관 태그로 분류."""
    rows = epeople_client.fetch_minwon(limit=min(sample, config.EPEOPLE_LIMIT))
    return [{
        "source": "국민신문고 민원 질의응답",
        "title": r["title"],
        "summary": "",
        "link": "",
        "date": r.get("date", ""),
        "meta": {"소관기관": r.get("agency", "")},
        "has_delegation": None,
        "reference_only": True,
    } for r in rows]


def _idea_signals(sample=100, **_) -> list[dict]:
    """국민생각함 국민제안(전국). 정책 수요 참고용 — 소관기관·처리상태 태그."""
    rows = epeople_client.fetch_ideas(limit=min(sample, config.EPEOPLE_LIMIT))
    signals = []
    for r in rows:
        meta = {"소관기관": r.get("agency", "")}
        if r.get("status"):
            meta["처리상태"] = r["status"]
        signals.append({
            "source": "국민생각함 정책제안",
            "title": r["title"],
            "summary": "",
            "link": "",
            "date": r.get("date", ""),
            "meta": meta,
            "has_delegation": None,
            "reference_only": True,
        })
    return signals


def _seminar_signals(sample=100, **_) -> list[dict]:
    """국회도서관 세미나 일정(열린국회정보 API). 정책 동향 참고용.

    세미나 제목은 조례명이 아니라 정책 주제라 매칭이 부정확 → 참고용으로만 노출.
    """
    rows = seminar_client.fetch_seminars(limit=min(sample, config.ASSEMBLY_SEMINAR_LIMIT))
    signals = []
    for r in rows:
        meta = {}
        if r.get("host"):
            meta["주최"] = r["host"]
        if r.get("place"):
            meta["장소"] = r["place"]
        signals.append({
            "source": "국회도서관 세미나",
            "title": r["title"],
            "summary": "",
            "link": r.get("link", ""),
            "date": r.get("date", ""),
            "meta": meta,
            "has_delegation": None,
            "reference_only": True,
        })
    return signals


def _demand_signals(sample=100, **_) -> list[dict]:
    """민원 등 현안 요구: 국민신문고·국민생각함·국회도서관 세미나를 한 카테고리로
    묶어, 현안 필요에 의한 조례 제·개정 후보로 처리한다 (참고용 아님).

    세 출처는 독립 API라 하나가 실패해도 나머지로 결과를 채운다.
    """
    signals, errors = [], []
    for fetch in (_minwon_signals, _idea_signals, _seminar_signals):
        try:
            signals += fetch(sample=sample)
        except (EpeopleError, AssemblyError) as exc:
            errors.append(str(exc))
    if not signals and errors:
        raise EpeopleError("; ".join(errors))
    # 인사·행사 등 비입법 제목은 추천 노이즈라 제외한다.
    signals = [s for s in signals if relevance.is_legislative(s["title"])]
    for sig in signals:
        sig.pop("reference_only", None)  # 현안 요구는 실제 제·개정 추천 대상
    return signals


def _policy_signals(sample=100, **_) -> list[dict]:
    """단계 ④⑤: 정부 정책브리핑·각 부처 보도자료 (RSS 피드).

    중앙정부의 새 정책·사업 신호를 받아 관련 경기도 조례 제·개정을 추천한다.
    """
    if not config.POLICY_FEEDS:
        raise RSSError("POLICY_FEEDS가 설정되지 않았습니다 (.env에 RSS 피드 URL 입력).")
    # 표본 수를 피드 수로 나눠 각 피드가 고르게 반영되도록 한다.
    per = max(1, -(-sample // len(config.POLICY_FEEDS)))
    signals = []
    for url in config.POLICY_FEEDS:
        for item in rss_client.fetch(url, limit=min(per, config.RSS_ITEM_LIMIT)):
            # 인사·행사 등 비입법 보도자료 제목은 추천 노이즈라 제외한다.
            if relevance.is_legislative(item.get("title", "")):
                signals.append({**item, "meta": {}})
    return signals[:sample]


# source 키 → (표시명, 신호 생성 함수)
SOURCES = {
    "assembly": ("국회 통과 법률안", _assembly_signals),
    "lawmaking": ("법제처 입법예고 (선제 대응)", _lawmaking_signals),
    "demand": ("민원 등 현안 요구 (제·개정 추천)", _demand_signals),
    "policy": ("정부 정책브리핑·부처 보도자료 (제·개정 추천)", _policy_signals),
}


def collect(source: str, **opts) -> list[dict]:
    if source not in SOURCES:
        raise ValueError(f"알 수 없는 출처: {source}")
    return SOURCES[source][1](**opts)


def council_in_progress_titles(limit: int = 50) -> list[str]:
    """경기도의회가 이미 입법예고한 조례안 제목 (중복 추천 방지용).

    중복 판정 보조 신호라, 의회 사이트가 막혀도 분석을 멈추지 않도록 실패 시 빈 목록.
    """
    try:
        rows = council_client.fetch_preannouncements(limit=min(limit, config.COUNCIL_LIMIT))
    except council_client.CouncilError:
        return []
    return [r["title"] for r in rows if r.get("title")]
