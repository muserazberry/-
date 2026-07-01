"""추천 엔진 집계·참고용 분류 회귀 테스트 (law_client 를 가짜로 대체)."""
import unittest

from app.analysis import recommender


class RecommendTest(unittest.TestCase):
    def setUp(self):
        # 조회되는 조례가 없도록 → 매칭 없는 신호는 'gap' 으로 판정된다.
        self._orig = recommender.law_client.search_ordinances
        recommender.law_client.search_ordinances = lambda term: []

    def tearDown(self):
        recommender.law_client.search_ordinances = self._orig

    def _sig(self, title, **extra):
        return {"title": title, "source": "t", "summary": "", "link": "",
                "date": "", "meta": {}, **extra}

    def test_no_match_counts_as_gap(self):
        out = recommender.recommend([self._sig("반려동물 보호법")])
        self.assertEqual(out["gap_count"], 1)
        self.assertEqual(out["candidates"][0]["level"], "gap")

    def test_reference_only_excluded_from_gap(self):
        out = recommender.recommend([self._sig("반려동물 보호법", reference_only=True)])
        self.assertEqual(out["gap_count"], 0)
        self.assertEqual(out["reference_count"], 1)
        self.assertFalse(out["candidates"][0]["gap"])

    def test_delegation_makes_strong_gap(self):
        out = recommender.recommend([self._sig("반려동물 보호법", has_delegation=True)])
        self.assertEqual(out["strong_gap_count"], 1)
        self.assertTrue(out["candidates"][0]["strong"])

    def test_reference_only_never_strong(self):
        out = recommender.recommend(
            [self._sig("반려동물 보호법", has_delegation=True, reference_only=True)])
        self.assertEqual(out["strong_gap_count"], 0)

    def test_reference_sorted_last(self):
        out = recommender.recommend([
            self._sig("반려동물 보호법", reference_only=True),
            self._sig("청년 기본법"),
        ])
        # 참고용은 항상 뒤로 정렬된다.
        self.assertFalse(out["candidates"][0]["reference_only"])
        self.assertTrue(out["candidates"][-1]["reference_only"])

    def test_titleless_signal_skipped(self):
        out = recommender.recommend([self._sig("")])
        self.assertEqual(out["total_scanned"], 0)

    def test_national_law_excluded_from_enact(self):
        # 위임조항 '없음' = 국가사무 → 미반영이어도 제정 추천에서 제외
        out = recommender.recommend([self._sig("병역법", has_delegation=False)])
        self.assertEqual(out["candidates"][0]["action"], "none")
        self.assertEqual(out["enact_count"], 0)
        self.assertEqual(out["gap_count"], 1)  # 원시 미반영 집계는 유지

    def test_local_gap_is_enact(self):
        out = recommender.recommend([self._sig("청년 기본법", has_delegation=True)])
        self.assertEqual(out["candidates"][0]["action"], "enact")
        self.assertEqual(out["enact_count"], 1)

    def test_in_progress_excluded_from_recommendation(self):
        # 같은 주제가 경기도의회 입법예고 중이면 추천하지 않고 '진행 중'으로 표시
        out = recommender.recommend(
            [self._sig("청년 기본법", has_delegation=True)],
            in_progress=["경기도 청년 기본 조례 일부개정조례안"])
        c = out["candidates"][0]
        self.assertTrue(c["in_progress"])
        self.assertEqual(c["action"], "none")
        self.assertEqual(out["enact_count"], 0)
        self.assertEqual(out["in_progress_count"], 1)
        self.assertFalse(c["gap"])

    def test_unrelated_in_progress_does_not_suppress(self):
        # 무관한 입법예고가 있어도 정상 추천은 유지된다
        out = recommender.recommend(
            [self._sig("청년 기본법", has_delegation=True)],
            in_progress=["경기도 상수도 급수 조례 일부개정조례안"])
        self.assertFalse(out["candidates"][0]["in_progress"])
        self.assertEqual(out["enact_count"], 1)


class ActionTest(unittest.TestCase):
    """권고 유형(_action) 순수 로직 테스트 (네트워크 없음)."""

    def test_weak_is_amend(self):
        self.assertEqual(recommender._action("weak", False, None, "x"), "amend")

    def test_reflected_is_none(self):
        self.assertEqual(recommender._action("reflected", False, True, "x"), "none")

    def test_reference_is_none(self):
        self.assertEqual(recommender._action("gap", True, True, "x"), "none")

    def test_gap_local_is_enact(self):
        self.assertEqual(recommender._action("gap", False, None, "청년 기본법"), "enact")

    def test_gap_national_is_none(self):
        self.assertEqual(recommender._action("gap", False, False, "병역법"), "none")

    def test_gap_other_region_is_none(self):
        self.assertEqual(
            recommender._action("gap", False, True, "제주특별자치도 설치 특별법"), "none")

    def test_national_directive_is_none(self):
        # 중앙정부 조직·직제령은 위임조항 미확인(None)이어도 자치사무가 아님
        self.assertEqual(
            recommender._action(
                "gap", False, None, "과학기술정보통신부와 그 소속기관 직제"), "none")

    def test_national_directive_not_amended_even_if_weak(self):
        # 직제령이 조례명과 부분 일치(weak)해도 개정 추천 대상이 아니다
        self.assertEqual(
            recommender._action("weak", False, None, "행정안전부 직제 일부개정령"), "none")


if __name__ == "__main__":
    unittest.main()
