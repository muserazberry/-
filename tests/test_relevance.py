"""비입법 신호 필터 회귀 테스트 (네트워크 불필요)."""
import unittest

from app.analysis.relevance import is_legislative


class RelevanceTest(unittest.TestCase):
    def test_rejects_personnel_and_events(self):
        # 인사·외교 의전·연예 등 조례와 무관한 제목은 걸러진다.
        self.assertFalse(is_legislative("외교부 신임 차관 임명"))
        self.assertFalse(is_legislative("MZ세대 겨냥 영화제 개막식 개최"))
        self.assertFalse(is_legislative("한미 정상회담 결과 발표"))

    def test_keeps_policy_titles(self):
        # 실제 정책·조례 주제는 통과한다.
        self.assertTrue(is_legislative("청소년 심리상담 지원 사업 확대"))
        self.assertTrue(is_legislative("1인가구 지원 강화 방안"))

    def test_does_not_drop_policy_words_resembling_noise(self):
        # '예방'·'방문'처럼 정책에도 흔한 단어는 노이즈로 보지 않는다.
        self.assertTrue(is_legislative("감염병 예방 대책 강화"))
        self.assertTrue(is_legislative("어린이 보호구역 현장 방문 점검"))

    def test_empty_title_is_allowed(self):
        self.assertTrue(is_legislative(""))


if __name__ == "__main__":
    unittest.main()
