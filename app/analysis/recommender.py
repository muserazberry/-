"""출처에 무관한 추천 엔진: 신호(signal) 목록을 경기도 조례와 대조한다.

signal = {"source", "title", "summary", "link", "date", "meta"}
title 에서 키워드를 뽑아 조례를 검색·판정한다. 국회 법안·정책 보도자료 등
모든 출처가 같은 형식의 signal 로 들어온다.
"""
from app.analysis import jurisdiction, matching
from app.analysis.keywords import expand_terms, search_terms
from app.clients import law_client

# 정렬 우선순위 (미반영 먼저, 그다음 유사도 낮은 순)
_LEVEL_ORDER = {"gap": 0, "weak": 1, "reflected": 2}
# 위임조항 우선순위 (있음 → 미확인 → 없음)
_DELEG_RANK = {True: 0, None: 1, False: 2}


def _action(level: str, ref_only: bool, has_delegation: bool | None, title: str) -> str:
    """후보를 권고 유형으로 분류한다: enact(제정) / amend(개정) / none(제외·반영).

    - gap(관련 조례 없음) + 자치사무 → 제정 추천(enact)
    - gap 이지만 국가사무·타지역 → 제외(none)
    - weak(관련 조례 있음, 부분 반영) → 개정 추천(amend)
    - reflected/참고용 → none
    """
    if ref_only or level == "reflected":
        return "none"
    if level == "weak":
        return "amend"
    # level == "gap"
    return "enact" if jurisdiction.is_local_matter(title, has_delegation) else "none"


def _ordinances_for(terms: list[str], linked: list[dict],
                    cache: dict[str, list[dict]]) -> list[dict]:
    """검색어(동의어 확장)로 조회한 조례와 공식 연계 조례를 합쳐 중복 제거한다."""
    merged: dict[str, dict] = {}
    for term in expand_terms(terms):
        if term not in cache:
            cache[term] = law_client.search_ordinances(term)
        for ordn in cache[term]:
            merged[ordn.get("ordin_id") or ordn.get("name")] = ordn
    # 공식 연계 조례는 키워드로 못 찾아도 후보에 포함하고 linked 표시를 유지한다.
    for ordn in linked:
        key = ordn.get("ordin_id") or ordn.get("name")
        merged[key] = {**merged.get(key, {}), **ordn}
    return list(merged.values())


def recommend(signals: list[dict]) -> dict:
    """각 신호를 경기도 조례와 대조해 미반영(추천) 후보를 만든다."""
    candidates = []
    cache: dict[str, list[dict]] = {}
    for sig in signals:
        terms = search_terms(sig.get("title", ""))
        if not terms:
            continue
        linked = sig.get("linked_ordinances") or []
        ranked = matching.rank_ordinances(sig["title"], _ordinances_for(terms, linked, cache))
        best = ranked[0] if ranked else None
        level = matching.classify(best)
        deleg = sig.get("has_delegation")
        # 참고용 신호(예산 등): 사업명↔조례명 매칭이 불확실해 확정 추천/갭으로 세지 않는다.
        ref_only = bool(sig.get("reference_only"))
        action = _action(level, ref_only, deleg, sig.get("title", ""))
        candidates.append({
            "signal": sig,
            "search_terms": terms,
            "level": level,
            "action": action,  # enact(제정) / amend(개정) / none(제외·반영)
            "reference_only": ref_only,
            "gap": level == "gap" and not ref_only,
            "has_delegation": deleg,
            "linked_count": len(linked),
            # 위임조항이 있는 미반영 = 고신뢰 추천 (참고용은 제외)
            "strong": level == "gap" and deleg is True and not ref_only,
            "best_score": best["score"] if best else 0.0,
            "matched_ordinances": ranked[:5],
            "match_count": len(ranked),
        })

    # 참고용은 뒤로 → 미반영 → 위임조항 있음 → 유사도 낮은 순
    candidates.sort(key=lambda c: (
        c["reference_only"], _LEVEL_ORDER[c["level"]],
        _DELEG_RANK.get(c["has_delegation"], 1), c["best_score"]))
    return {
        "total_scanned": len(candidates),
        "gap_count": sum(1 for c in candidates if c["gap"]),
        "strong_gap_count": sum(1 for c in candidates if c["strong"]),
        "weak_count": sum(1 for c in candidates if c["level"] == "weak" and not c["reference_only"]),
        "reference_count": sum(1 for c in candidates if c["reference_only"]),
        # 권고 유형별 집계 (자치사무 필터 적용 후)
        "enact_count": sum(1 for c in candidates if c["action"] == "enact"),
        "amend_count": sum(1 for c in candidates if c["action"] == "amend"),
        "candidates": candidates,
    }
