"""법률안 제목과 조례명 간 관련성 판정.

핵심 신호: 법률안의 주제어가 조례명에 들어있는가(토큰 포함).
보조 신호: 글자 바이그램 유사도(같은 등급 안에서 정렬·표시용).
한국어 합성어·띄어쓰기 차이에 강하도록 일반어를 지운 압축 문자열로 비교한다.
"""
import re

from app.analysis.keywords import _GENERIC, canonicalize, tokens


def _norm(text: str) -> str:
    """동의어 통일 후 공백·일반어를 제거한 압축 문자열."""
    text = canonicalize(text)
    for word in _GENERIC:
        text = text.replace(word, "")
    return re.sub(r"\s+", "", text)


def similarity(a: str, b: str) -> float:
    """두 제목의 글자 바이그램 Jaccard 유사도 (0~1, 보조 신호)."""
    na, nb = _norm(a), _norm(b)
    ga = {na[i:i + 2] for i in range(len(na) - 1)}
    gb = {nb[i:i + 2] for i in range(len(nb) - 1)}
    if not ga or not gb:
        return 0.0
    return round(len(ga & gb) / len(ga | gb), 3)


def _key_tokens(bill_name: str) -> list[str]:
    """일반어를 지운 길이 2 이상의 핵심 토큰."""
    return [t for t in (_norm(x) for x in tokens(bill_name)) if len(t) >= 2]


def rank_ordinances(bill_name: str, ordinances: list[dict]) -> list[dict]:
    """조례 후보에 (핵심어 일치·토큰 적중수·유사도)를 붙여 관련도 높은 순으로 정렬."""
    keys = _key_tokens(bill_name)
    primary = max(keys, key=len) if keys else ""
    scored = []
    for ordn in ordinances:
        norm_name = _norm(ordn.get("name", ""))
        scored.append({
            **ordn,
            "score": similarity(bill_name, ordn.get("name", "")),
            "hits": sum(1 for t in keys if t in norm_name),
            "key_match": bool(primary and primary in norm_name),
            "linked": bool(ordn.get("linked")),
        })
    # 공식 연계(linked) 조례를 최우선으로 정렬
    scored.sort(key=lambda o: (o["linked"], o["key_match"], o["hits"], o["score"]), reverse=True)
    return scored


def classify(best: dict | None) -> str:
    """가장 관련도 높은 조례 기준으로 반영 수준 판정: reflected / weak / gap."""
    if not best:
        return "gap"
    # 공식 연계 또는 핵심어 일치 → 이미 반영됨
    if best.get("linked") or best["key_match"]:
        return "reflected"
    if best["hits"] >= 1:
        return "weak"
    return "gap"
