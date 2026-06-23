# -*- coding: utf-8 -*-
"""경기도 조례 제·개정 추천 현황 보고서 생성 (일회성 스크립트)."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.analysis.gap_finder import analyze


def _ordn_names(cands, n=2):
    names = [o.get("name", "") for o in cands[:n] if o.get("name")]
    return ", ".join(names) if names else "-"


def run(source, label, sample):
    res = analyze(source=source, sample=sample, only_passed=True, with_delegation=True)
    cs = res["candidates"]
    enact = [c for c in cs if c["action"] == "enact"]                               # 제정(자치사무 필터 적용)
    amend = [c for c in cs if c["action"] == "amend"]                               # 개정
    excluded = [c for c in cs if c["level"] == "gap" and c["action"] == "none"
                and not c["reference_only"]]                                        # 국가사무·타지역 제외
    done = [c for c in cs if c["level"] == "reflected"]                              # 이미 반영

    print(f"\n## {label}")
    print(f"- 분석한 신호: {res['total_scanned']}건")
    print(f"- **제정 추천: {len(enact)}건** (관련 경기도 조례 없음 + 자치사무 → 신규 제정 검토)")
    print(f"- **개정 추천: {len(amend)}건** (관련 조례는 있으나 부분 반영 → 개정 검토)")
    print(f"- 국가사무·타지역으로 제외: {len(excluded)}건 (미반영이지만 경기도 제정 대상 아님)")
    print(f"- 이미 반영(조치 불필요): {len(done)}건")
    print(f"  - 그중 위임조항 확인된 고신뢰 제정 추천: {res['strong_gap_count']}건")

    if enact:
        print("\n### [제정 추천] 새 조례가 필요한 법률")
        for c in enact:
            sig = c["signal"]
            deleg = {True: "위임조항 있음", False: "위임조항 없음", None: "위임 확인불가"}[c["has_delegation"]]
            link = (sig.get("meta") or {}).get("연계조례", "")
            extra = f" / {link}" if link else ""
            print(f"- {sig['title']}  ({deleg}{extra})")

    if amend:
        print("\n### [개정 추천] 기존 조례 보완이 필요한 법률")
        for c in amend:
            sig = c["signal"]
            rel = _ordn_names(c["matched_ordinances"])
            print(f"- {sig['title']}")
            print(f"    └ 관련 기존 조례: {rel}")


print("# 경기도 조례 제·개정 추천 현황")
print("출처: 국회 통과 법률안(22대) → 경기도 자치법규 대조 (자동 생성)")
run("assembly", "국회 통과 법률안 기준", sample=60)
print("\n(참고) 자치사무 필터 적용. 국민신문고·국민생각함 등 '참고용'은 제외.")
