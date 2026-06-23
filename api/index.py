"""Vercel 서버리스 진입점.

기존 FastAPI 앱(app.api.main:app)을 그대로 노출한다. Vercel Python 런타임이
`app` (ASGI) 을 감지해 서버 없이 함수로 실행한다. app 패키지는 import 추적으로
자동 번들되고, 정적 파일(web/)은 vercel.json 의 includeFiles 로 포함한다.
"""
from app.api.main import app  # noqa: F401  (Vercel 이 이 `app` 을 사용)
