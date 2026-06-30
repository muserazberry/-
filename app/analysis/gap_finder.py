"""오케스트레이터: 선택한 출처의 신호를 모아 추천 엔진에 넘긴다."""
from app import sources
from app.analysis.recommender import recommend


def analyze(source: str = "assembly", age: str | None = None, sample: int = 100,
            only_passed: bool = True, with_delegation: bool = True) -> dict:
    """출처(source)별 신호를 수집해 경기도 조례 미반영 후보를 만든다."""
    signals = sources.collect(source, age=age, sample=sample,
                              only_passed=only_passed, with_delegation=with_delegation)
    # 경기도의회가 이미 입법예고 중인 주제는 중복이라 추천에서 뺀다.
    in_progress = sources.council_in_progress_titles()
    result = recommend(signals, in_progress=in_progress)
    result["source"] = source
    result["source_label"] = sources.SOURCES[source][0]
    result["generated_for"] = age
    return result
