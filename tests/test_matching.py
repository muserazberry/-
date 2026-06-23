"""조례 매칭·반영수준 판정 회귀 테스트 (네트워크 불필요)."""
import unittest

from app.analysis.matching import classify, rank_ordinances, similarity


class SimilarityTest(unittest.TestCase):
    def test_identical_titles_high(self):
        self.assertGreater(similarity("청년 기본 조례", "청년 기본 조례"), 0.9)

    def test_unrelated_titles_low(self):
        self.assertEqual(similarity("반려동물", "탄소중립"), 0.0)


class RankTest(unittest.TestCase):
    def test_key_match_detected(self):
        ranked = rank_ordinances(
            "인공지능 진흥법 일부개정법률안",
            [{"name": "경기도 인공지능 산업 육성 조례", "ordin_id": "1"}])
        self.assertTrue(ranked[0]["key_match"])
        self.assertGreaterEqual(ranked[0]["hits"], 1)

    def test_linked_sorts_first(self):
        ranked = rank_ordinances("청년 기본법", [
            {"name": "경기도 무관 조례", "ordin_id": "1"},
            {"name": "경기도 청년 연계 조례", "ordin_id": "2", "linked": True},
        ])
        self.assertTrue(ranked[0]["linked"])


class ClassifyTest(unittest.TestCase):
    def test_none_is_gap(self):
        self.assertEqual(classify(None), "gap")

    def test_key_match_is_reflected(self):
        self.assertEqual(
            classify({"linked": False, "key_match": True, "hits": 1, "score": 0.3}),
            "reflected")

    def test_linked_is_reflected(self):
        self.assertEqual(
            classify({"linked": True, "key_match": False, "hits": 0, "score": 0.0}),
            "reflected")

    def test_partial_hit_is_weak(self):
        self.assertEqual(
            classify({"linked": False, "key_match": False, "hits": 1, "score": 0.1}),
            "weak")

    def test_no_hit_is_gap(self):
        self.assertEqual(
            classify({"linked": False, "key_match": False, "hits": 0, "score": 0.0}),
            "gap")


if __name__ == "__main__":
    unittest.main()
