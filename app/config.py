"""환경설정 및 상수 로딩."""
import os
from dotenv import load_dotenv

load_dotenv()

# 국가법령정보센터: OC는 신청 이메일의 ID 부분
LAW_OC = os.getenv("LAW_OC", "test")
LAW_BASE = "https://www.law.go.kr/DRF"
# 법령 → 연계 자치법규 목록 조회 서비스 target (법령명으로 조회). 공식 매핑.
LAW_LINK_TARGET = os.getenv("LAW_LINK_TARGET", "lnkLs")

# 열린국회정보
ASSEMBLY_KEY = os.getenv("ASSEMBLY_KEY", "")
ASSEMBLY_BILL_SERVICE = os.getenv("ASSEMBLY_BILL_SERVICE", "TVBPMBILL11")
ASSEMBLY_AGE = os.getenv("ASSEMBLY_AGE", "22")
ASSEMBLY_BASE = "https://open.assembly.go.kr/portal/openapi"
# 국회도서관 '국회의원 세미나 일정' 서비스 ID (열린국회정보, ASSEMBLY_KEY 재사용).
# 공식 서비스(국회도서관 제공, 무료·실시간):
#   https://open.assembly.go.kr/portal/data/service/selectServicePage.do?infId=O67B1I001080WL10254
# 법률안 서비스처럼 본인 대시보드 'OPEN API 신청' 후 영문 서비스명을 확인해 입력한다.
ASSEMBLY_SEMINAR_SERVICE = os.getenv("ASSEMBLY_SEMINAR_SERVICE", "")
ASSEMBLY_SEMINAR_LIMIT = int(os.getenv("ASSEMBLY_SEMINAR_LIMIT", "60"))

# 정부입법지원센터 입법예고 (선제 대응용). OC는 법제처 동일 계정이라 LAW_OC 재사용.
# API가 opinion.lawmaking.go.kr 로 이전됨: 목록은 /ogLmPp.xml (확장자 형식).
LAWMAKING_OC = os.getenv("LAWMAKING_OC", "") or LAW_OC
LAWMAKING_BASE = "https://opinion.lawmaking.go.kr/rest"
LAWMAKING_LIMIT = int(os.getenv("LAWMAKING_LIMIT", "100"))

# 경기도의회 입법예고(조례안) 게시판 — RSS·API가 없어 HTML 목록을 직접 파싱.
COUNCIL_SITE = "https://www.ggc.go.kr"
COUNCIL_BASE = COUNCIL_SITE + "/site/main/board/lgslt"
COUNCIL_LIMIT = int(os.getenv("COUNCIL_LIMIT", "100"))

# 국민신문고 민원 질의응답 / 국민생각함 국민제안 게시판 (전국 단위, HTML 파싱).
# 인증키 없이 목록 HTML을 직접 긁는다. 소관기관은 메타 태그로 보관(참고용).
EPEOPLE_MINWON_URL = "https://www.epeople.go.kr/nep/pttn/gnrlPttn/pttnSmlrCaseList.npaid"
EPEOPLE_IDEA_URL = "https://www.epeople.go.kr/nep/prpsl/opnPrpl/opnpblPrpslList.npaid"
EPEOPLE_LIMIT = int(os.getenv("EPEOPLE_LIMIT", "60"))

# 경기도 자치법규 필터링 기준 (지자체기관명에 포함되는 문자열)
GYEONGGI_ORG = "경기도"

# 경기도 예산·업무보고 (세출예산 CSV) — 신규/대규모/증액 사업을 조례와 대조.
BUDGET_FILE = os.getenv("BUDGET_FILE", "")
BUDGET_TOP_N = int(os.getenv("BUDGET_TOP_N", "30"))          # 금액 상위 N개 = '대규모'
BUDGET_INCREASE_PCT = float(os.getenv("BUDGET_INCREASE_PCT", "0.5"))  # 전년 대비 +50% = '증액'
# True면 신규·대규모·증액 사업만 추린다 (검토 대상 집중).
BUDGET_ONLY_FLAGGED = os.getenv("BUDGET_ONLY_FLAGGED", "true").lower() != "false"

# 정책/보도자료 RSS 피드 URL (쉼표 구분). 정부 정책브리핑·경기도 등.
# 예) POLICY_FEEDS=https://www.korea.kr/rss/policy.xml,https://www.gg.go.kr/rss/news.xml
POLICY_FEEDS = [u.strip() for u in os.getenv("POLICY_FEEDS", "").split(",") if u.strip()]
RSS_ITEM_LIMIT = int(os.getenv("RSS_ITEM_LIMIT", "40"))

REQUEST_TIMEOUT = 20.0
