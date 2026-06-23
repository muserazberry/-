"""FastAPI 백엔드: 분석 결과 API + 대시보드 정적 페이지 제공."""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from app.analysis.gap_finder import analyze
from app.clients.assembly_client import AssemblyError
from app.clients.budget_client import BudgetError
from app.clients.council_client import CouncilError
from app.clients.epeople_client import EpeopleError
from app.clients.law_client import LawError
from app.clients.lawmaking_client import LawmakingError
from app.clients.rss_client import RSSError
from app.sources import SOURCES

WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="경기도 조례 제·개정 추천 시스템", version="0.1.0")


@app.get("/api/sources")
def api_sources():
    """선택 가능한 신호 출처 목록."""
    return [{"key": k, "label": label} for k, (label, _) in SOURCES.items()]


@app.get("/api/analyze")
def api_analyze(
    source: str = Query(default="assembly", description="신호 출처 (assembly/policy)"),
    age: str | None = Query(default=None, description="국회 대수 (기본: .env ASSEMBLY_AGE)"),
    sample: int = Query(default=100, ge=1, le=100),
    only_passed: bool = Query(default=True),
    with_delegation: bool = Query(default=True, description="법령 본문 위임조항 분석 (assembly)"),
):
    try:
        return analyze(source=source, age=age, sample=sample,
                       only_passed=only_passed, with_delegation=with_delegation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AssemblyError as exc:
        raise HTTPException(status_code=502, detail=f"국회 API 오류: {exc}") from exc
    except BudgetError as exc:
        raise HTTPException(status_code=400, detail=f"예산 자료 오류: {exc}") from exc
    except CouncilError as exc:
        raise HTTPException(status_code=502, detail=f"의회 입법예고 수집 오류: {exc}") from exc
    except EpeopleError as exc:
        raise HTTPException(status_code=502, detail=f"국민신문고 수집 오류: {exc}") from exc
    except RSSError as exc:
        raise HTTPException(status_code=502, detail=f"RSS 오류: {exc}") from exc
    except LawmakingError as exc:
        raise HTTPException(status_code=502, detail=f"입법예고 API 오류: {exc}") from exc
    except LawError as exc:
        raise HTTPException(status_code=502, detail=f"법령센터 API 오류: {exc}") from exc


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")
