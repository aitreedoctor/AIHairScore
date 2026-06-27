import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "scalp_care.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception as e:
        print(f"[Database] Failed to set WAL mode: {e}")
    return conn

def init_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. scalp_reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scalp_reports (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        family_history TEXT NOT NULL,
        subjective_symptoms TEXT NOT NULL, -- JSON string
        location TEXT NOT NULL,
        redness INTEGER NOT NULL,
        dead_skin INTEGER NOT NULL,
        sebum INTEGER NOT NULL,
        hair_density INTEGER NOT NULL,
        hair_thickness INTEGER NOT NULL,
        overall_score INTEGER NOT NULL,
        overall_grade TEXT NOT NULL,
        ai_opinion TEXT NOT NULL,
        homecare_solution TEXT NOT NULL,
        offline_proposal TEXT NOT NULL,
        pdf_url TEXT,
        raw_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. scalp_partners table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scalp_partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- '피부과의원', '두피케어센터'
        address TEXT NOT NULL,
        phone TEXT NOT NULL,
        benefit TEXT NOT NULL
    );
    """)
    
    # Check if scalp_partners is empty, then seed it
    cursor.execute("SELECT COUNT(*) FROM scalp_partners")
    if cursor.fetchone()[0] == 0:
        partners = [
            ("안티그래비티 두피케어 강남본점", "두피케어센터", "서울시 강남구 테헤란로 123", "02-555-9876", "비전 AI 연계 정밀 현미경 무료 검사 & 케어 프로그램 20% 할인"),
            ("청담 민 피부과의원", "피부과의원", "서울시 강남구 압구정로 456", "02-3444-1111", "모낭 정밀 진단 의사 초진 진료비 30% 감면 및 맞춤 토닉 증정"),
            ("웰니스 탈모케어 서초점", "두피케어센터", "서울시 서초구 서초중앙로 78", "02-588-2233", "두피 스케일링 체험 1회 무료 제공 (초진 연계 시)"),
            ("서울대 입구 리치 두피센터", "두피케어센터", "서울시 관악구 관악로 152", "02-888-7744", "정밀 모근 분석 및 두피 장벽 개선 앰플 샘플 키트 증정"),
            ("마포 헤어 웰니스 의원", "피부과의원", "서울시 마포구 독막로 89", "02-711-5500", "두피 열성 홍반 케어 첫 방문 15% 웰니스 혜택 제공"),
            ("여의도 더 스칼프 메디컬", "피부과의원", "서울시 영등포구 여의대로 108", "02-761-9988", "디지털 현미경 모근 밀도 측정 무료 및 맞춤 홈케어 솔루션 가이드 제공"),
            ("분당 정자 두피연구소", "두피케어센터", "경기도 성남시 분당구 정자일로 210", "031-712-4455", "두피 각질 딥 스케일링 관리 20% 제휴 할인"),
            ("부산 해운대 스칼프 스파", "두피케어센터", "부산시 해운대구 우동 627", "051-744-8800", "정밀 두피 장벽 진단 및 안티헤어 로스 토닉 증정"),
            ("대구 동성로 탈모 크리닉", "피부과의원", "대구시 중구 동성로 36", "053-425-6677", "유전성 두피 장벽 웰니스 모니터링 상담 무료 및 홈케어 팩 증정"),
            ("광주 상무 두피케어 웰니스", "두피케어센터", "광주시 서구 상무중앙로 80", "062-373-1122", "모발 밀도 및 두피 유분 검사 무료 체험 제공")
        ]
        cursor.executemany("""
        INSERT INTO scalp_partners (name, category, address, phone, benefit)
        VALUES (?, ?, ?, ?, ?)
        """, partners)
        conn.commit()
        print("[Database] Successfully seeded scalp partners.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
