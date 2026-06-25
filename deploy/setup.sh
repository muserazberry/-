#!/usr/bin/env bash
# 경기도 조례 시스템 - 우분투(Ubuntu/Debian) 서버 초기 설치 스크립트.
# Google Cloud VM·NCP 등 어디서나 동일하게 동작한다.
# 사용법:  bash setup.sh
set -e

echo "[1/4] 패키지 설치 (python3, venv, git)…"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git

echo "[2/4] 소스 내려받기…"
cd ~
if [ -d ordinance ]; then
  cd ordinance && git pull
else
  git clone https://github.com/muserazberry/-.git ordinance
  cd ordinance
fi

echo "[3/4] 가상환경 + 의존성 설치…"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "[4/4] 완료."
echo "다음 단계:"
echo "  1) ~/ordinance/.env 파일을 만들어 API 키를 입력하세요 (.env.example 참고)."
echo "  2) systemd 서비스를 등록하세요 (deploy/ordinance.service 참고)."
