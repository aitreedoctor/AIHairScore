@echo off
title Anti-Gravity AI Hair Score - 원클릭 서버 실행기
chcp 65001 > nul

echo ===================================================
echo   🧬 Anti-Gravity AI Hair Score 🧬
echo   두피/모발 웰니스 AI 케어 플랫폼 원클릭 구동기
echo ===================================================
echo.

:: 1. .env 파일이 존재하지 않는 경우 자동 복사 및 안내
if not exist ".env" (
    echo [안내] 환경 변수 설정 파일 .env 이 존재하지 않아 .env.example로부터 자동 복제합니다.
    copy .env.example .env > nul
    echo.
    echo ---------------------------------------------------
    echo   [⚠️ 필독 - API Key 설정 필수]
    echo   프로젝트 루트 폴더에 생성된 '.env' 파일을 메모장으로 열어 
    echo   실제 사용할 Gemini API Key 등을 입력하고 저장해 주세요!
    echo ---------------------------------------------------
    echo.
    pause
)

:: 2. 가상환경(venv) 존재 여부 체크 및 생성
if not exist "venv" (
    echo [1/3] 파이썬 가상환경 venv이 존재하지 않아 새로 생성합니다...
    python -m venv venv
    if errorlevel 1 (
        echo [에러] 파이썬 Python이 이 시스템에 설치되어 있지 않거나 PATH 등록이 되어 있지 않습니다.
        echo https://www.python.org 에서 Python 3.10 이상 버전을 다운로드하여 설치해 주세요.
        echo [필독] 설치 시 'Add Python to PATH' 옵션을 반드시 체크해야 합니다.
        echo.
        pause
        exit /b
    )
    echo [성공] 가상환경 생성이 완료되었습니다.
    echo.
) else (
    echo [1/3] 기존 생성된 파이썬 가상환경 venv 을 감지했습니다.
)

:: 3. 가상환경 활성화 및 패키지 설치
echo [2/3] 필요한 의존성 라이브러리(FastAPI, ReportLab, Google-GenAI 등)를 설치 및 업데이트합니다...
call venv\Scripts\activate.bat
venv\Scripts\python.exe -m pip install --upgrade pip > nul
venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [에러] 라이브러리 설치 중 오류가 발생했습니다. 인터넷 연결 상태를 확인해 주세요.
    echo.
    pause
    exit /b
)
echo [성공] 필수 라이브러리 설치가 완료되었습니다.
echo.

:: 4. 백엔드 데이터베이스 체크 및 생성
echo [3/3] 필수 데이터베이스 파일 유무를 검사합니다...
if not exist "backend\scalp_care.db" (
    echo [정보] 데이터베이스 파일이 존재하지 않아 새로 초기화합니다...
    venv\Scripts\python.exe backend\db.py
)
echo [성공] 데이터베이스 및 제휴 지점 데이터가 준비되었습니다.
echo.

:: 5. 서버 가동 및 브라우저 열기
echo ===================================================
echo   🚀 Anti-Gravity AI Hair Score FastAPI 서버를 가동합니다.
echo   자동으로 기본 웹 브라우저에서 진단 사이트(localhost:8001)를 엽니다.
echo   (이 콘솔 창을 닫으면 서버가 종료됩니다)
echo ===================================================
echo.

:: 2초 대기 후 브라우저 오픈
ping 127.0.0.1 -n 3 > nul
start http://localhost:8001

:: uvicorn 실행
venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
if errorlevel 1 (
    echo.
    echo [⚠️ 에러] 로컬 서버 구동 도중 오류가 발생해 비정상 종료되었습니다.
    echo          포트 충돌 8001번 또는 라이브러리 누락 여부를 확인하세요.
    echo.
    pause
)
