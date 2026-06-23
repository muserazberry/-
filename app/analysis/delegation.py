"""법령 본문에서 '조례 위임조항'을 탐지한다.

위임조항(예: "…는 조례로 정한다")이 있으면 그 법은 지방자치단체가 조례로
정하도록 위임한 것이므로, 경기도 미반영 시 추천 신뢰도가 크게 높아진다.
"""
import re

# 조례 위임을 나타내는 대표 표현
_PATTERNS = [
    r"조례로\s*정(한다|하는|할\s*수\s*있다|하여야)",
    r"조례가\s*정하는\s*바",
    r"조례로\s*정하는\s*바",
    r"(지방자치단체|특별시|광역시|특별자치시|특별자치도|시[\s·]?도|시[\s·]?군[\s·]?구)의?\s*조례",
    r"자치법규로\s*정",
    r"조례\s*(또는|및)\s*규칙으로\s*정",
]
_RE = re.compile("|".join(_PATTERNS))


def scan(text: str, window: int = 35, limit: int = 3) -> dict:
    """본문에서 위임조항 존재 여부와 근거 스니펫(주변 문맥)을 돌려준다."""
    if not text:
        return {"found": False, "snippets": []}
    snippets: list[str] = []
    for m in _RE.finditer(text):
        start = max(0, m.start() - window)
        snippet = re.sub(r"\s+", " ", text[start:m.end() + window]).strip()
        if snippet not in snippets:
            snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return {"found": bool(snippets), "snippets": snippets}
