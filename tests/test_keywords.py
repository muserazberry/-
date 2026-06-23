"""키워드 추출·동의어 통일 회귀 테스트 (네트워크 불필요)."""
import unittest

from app.analysis.keywords import (canonicalize, clean, expand_terms,
                                    search_terms, tokens)


class CleanTest(unittest.TestCase):
    def test_strips_bracket_and_law_tail(self):
        self.assertEqual(clean("인공지능 진흥법 일부개정법률안"), "인공지능 진흥법")

    def test_strips_gwanhan_form(self):
        self.assertEqual(clean("저출생 극복에 관한 법률"), "저출생 극복")


class TokensTest(unittest.TestCase):
    def test_drops_generic_and_short_tokens(self):
        # '및','등','지원' 같은 일반어와 1글자 토큰은 제외된다.
        self.assertNotIn("지원", tokens("청년 지원 및 육성 조례안"))

    def test_keeps_meaningful_tokens(self):
        self.assertIn("청년", tokens("청년 지원 및 육성 조례안"))


class SearchTermsTest(unittest.TestCase):
    def test_picks_longest_first_max_k(self):
        # 긴 도메인어 우선, 최대 k개 ('지원'은 일반어로 제외).
        self.assertEqual(
            search_terms("노인 일자리 지원에 관한 법률 일부개정법률안"),
            ["일자리", "노인"])

    def test_filler_words_dropped(self):
        # 행정 상투어('진흥')는 걸러지고 도메인어만 남는다.
        self.assertEqual(
            search_terms("인공지능 진흥에 관한 법률 일부개정법률안"),
            ["인공지능"])

    def test_never_empty_when_title_present(self):
        # 토큰이 전부 일반어로 걸러져도 clean 결과로 폴백한다.
        self.assertTrue(search_terms("지원에 관한 법률"))


class SynonymTest(unittest.TestCase):
    def test_canonicalize_maps_variant_to_representative(self):
        self.assertEqual(canonicalize("AI 기본법"), "인공지능 기본법")
        self.assertEqual(canonicalize("저출산 대책"), "저출생 대책")

    def test_expand_adds_group_members(self):
        out = expand_terms(["노인"])
        self.assertIn("노인", out)
        self.assertIn("고령자", out)
        self.assertIn("어르신", out)

    def test_expand_is_noop_for_non_synonym(self):
        self.assertEqual(expand_terms(["반려동물"]), ["반려동물"])


if __name__ == "__main__":
    unittest.main()
