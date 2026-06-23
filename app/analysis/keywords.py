"""법률안 제목에서 조례 매칭용 키워드/토큰을 추출한다."""
import re

# 제목 꼬리에 붙는 법률 형식 표현 (긴 것부터 제거)
_TAIL_PATTERNS = [
    r"일부개정법률안$", r"전부개정법률안$", r"제정법률안$", r"폐지법률안$",
    r"개정법률안$", r"제정안$", r"법률안$", r"법안$",
    r"등에\s*관한\s*법률$", r"에\s*관한\s*법률$", r"에\s*관한\s*특별법$",
    r"특별법$", r"기본법$", r"법률$",
]

# 검색·점수에서 의미가 없는 일반어/형식어
# (행정 상투어 '육성·진흥·관리…'는 도메인 단어가 아니라 잘못된 매칭을 유발하므로 제외)
_GENERIC = {
    "관한", "대한", "관련", "위한", "위하여", "따른", "등", "및", "법", "법률",
    "법안", "특별법", "기본법", "일부", "전부", "개정", "제정", "폐지", "조례",
    "규칙", "경기도", "지원", "촉진",
    "육성", "진흥", "관리", "활성화", "운영", "이용", "추진", "활용",
    "예방", "보호", "조성", "보급", "증진",
}

# 토큰 끝에 흔히 붙는 조사 (1회 제거)
_JOSA = re.compile(r"(에서|으로|에게|에|를|을|과|와|의|은|는|이|가|도|등)$")

# 동의어·약어 그룹: 표현이 달라 매칭을 놓치는 경우를 줄인다.
# 각 그룹의 첫 항목을 대표어로 삼아 canonicalize 가 나머지를 대표어로 치환한다.
# (검색 재현율 ↑ + 법안·조례 표기 차이 흡수)
_SYNONYM_GROUPS = [
    ("인공지능", "AI", "에이아이"),
    ("1인가구", "일인가구", "단독가구"),
    ("고령자", "노인", "어르신"),
    ("영유아", "보육", "어린이집"),
    ("장애인", "장애우"),
    ("탄소중립", "기후위기", "기후변화"),
    ("소상공인", "자영업자"),
    ("전기자동차", "전기차"),
    ("저출생", "저출산"),
    ("다문화", "외국인주민"),
    ("지역화폐", "지역사랑상품권", "지역상품권"),
]
_CANON = {v: g[0] for g in _SYNONYM_GROUPS for v in g}
# 긴 변형부터 치환해 부분 겹침을 피한다.
_VARIANTS = sorted(_CANON, key=len, reverse=True)


def canonicalize(text: str) -> str:
    """동의어·약어를 대표어로 통일한다 (예: 'AI' → '인공지능')."""
    for v in _VARIANTS:
        if v in text:
            text = text.replace(v, _CANON[v])
    return text


def expand_terms(terms: list[str]) -> list[str]:
    """검색어에 같은 그룹의 동의어를 더해 재현율을 높인다 (중복 제거)."""
    out = list(terms)
    for term in terms:
        for group in _SYNONYM_GROUPS:
            if term in group:
                out.extend(v for v in group if v != term)
    return list(dict.fromkeys(out))


def clean(bill_name: str) -> str:
    """괄호·법률 형식 꼬리를 제거한 핵심 제목을 돌려준다."""
    text = re.sub(r"\(.*?\)", "", bill_name or "").strip()
    for pat in _TAIL_PATTERNS:
        text = re.sub(pat, "", text).strip()
    return text


def tokens(bill_name: str) -> list[str]:
    """조사·일반어를 제거한 의미 토큰 목록."""
    result = []
    for raw in clean(bill_name).split():
        tok = _JOSA.sub("", raw)
        if len(tok) >= 2 and tok not in _GENERIC:
            result.append(tok)
    return result


def search_terms(bill_name: str, k: int = 2) -> list[str]:
    """법령센터 검색에 쓸 핵심어 후보 (긴 토큰 우선, 최대 k개)."""
    uniq = list(dict.fromkeys(tokens(bill_name)))
    uniq.sort(key=len, reverse=True)
    return uniq[:k] or ([clean(bill_name)] if clean(bill_name) else [])
