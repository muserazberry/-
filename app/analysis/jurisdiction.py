"""국가사무·타지역 전용 법률을 가려 '제정 추천' 오탐을 줄인다.

핵심 휴리스틱:
- 조례 위임조항이 '없음(False)'으로 확인된 법은 국가사무로 보고 제외한다.
- 다른 지역 전용 특별법(제주·세종·강원·전북특별자치도 등)은 경기도와 무관해 제외한다.
- 위임조항이 '있음(True)/확인불가(None)'면 자치사무 가능성이 있어 후보로 남긴다.
"""
import re

# 다른 지역 전용 법률 (경기도 조례 대상이 아님)
_OTHER_REGION = re.compile(
    r"(제주특별자치도|세종특별자치시|강원특별자치도|전북특별자치도)")


def is_local_matter(title: str, has_delegation: bool | None) -> bool:
    """제목·위임조항으로 경기도 자치사무(조례 제정) 대상일 가능성을 판정한다."""
    if _OTHER_REGION.search(title or ""):
        return False
    if has_delegation is False:
        return False
    return True
