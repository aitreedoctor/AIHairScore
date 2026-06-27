import os
import sys
import json
from fastapi.testclient import TestClient

# Add workspace directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

client = TestClient(app)

def test_partners_endpoint():
    print("[TEST] Testing /api/v1/scalp/partners...")
    response = client.get("/api/v1/scalp/partners?location=강남구")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    print(f"[OK] Found {len(data)} partners in Gangnam.")
    for p in data:
        print(f"     - {p['name']} ({p['address']})")

def test_history_endpoint():
    print("[TEST] Testing /api/v1/scalp/history?user_id=all...")
    response = client.get("/api/v1/scalp/history?user_id=all")
    assert response.status_code == 200
    data = response.json()
    print(f"[OK] Found {len(data)} historical records.")
    for item in data:
        assert "age" in item
        assert "gender" in item

def test_safety_filter():
    print("[TEST] Testing safety filter post-processing...")
    test_phrase = "현 상태는 지루성 탈모증으로 진단됩니다. 샴푸와 피나스테리드 약처방을 병행하여 치료해야 합니다."
    response = client.post("/api/v1/scalp/test-safety-filter", data={"text": test_phrase})
    assert response.status_code == 200
    data = response.json()
    
    # Confirm replacements happened
    assert data["is_safe"] is True or data["filtered"] != test_phrase
    assert "진단" not in data["filtered"]
    assert "처방" not in data["filtered"]
    assert "탈모증" not in data["filtered"]
    assert "치료" not in data["filtered"]
    
    print("[OK] Safety filter successfully converted forbidden medical words:")
    print(f"     Original: {data['original']}")
    print(f"     Filtered: {data['filtered']}")
    print(f"     Detected: {data['detected']}")

def test_diagnose_endpoint():
    print("[TEST] Testing /api/v1/scalp/diagnose (LLM mock parameters)...")
    payload = {
        "user_id": "test_user_1",
        "vision_analysis": {
            "redness": 2,
            "dead_skin": 1,
            "sebum": 3,
            "hair_density": 2,
            "hair_thickness": 1
        },
        "user_survey": {
            "age": 34,
            "gender": "male",
            "family_history": "paternal_side",
            "subjective_symptoms": ["두피 열감이 심함", "오후에 기름이 많이 짐"]
        },
        "location": "서울시 강남구"
    }
    
    # Check if Gemini key is set before running AI test to avoid failures on missing keys
    api_key = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARNING] Skipping diagnose AI endpoint test due to missing GEMINI_API_KEY.")
        return
        
    response = client.post("/api/v1/scalp/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "overall_score" in data
    assert "overall_grade" in data
    assert "ai_opinion" in data
    assert "homecare_solution" in data
    assert "offline_proposal" in data
    
    print("[OK] /api/v1/scalp/diagnose executed successfully.")
    print(f"     Overall Score: {data['overall_score']}")
    print(f"     Overall Grade: {data['overall_grade']}")
    
    report_id = data.get("id")
    if report_id:
        print(f"[TEST] Testing /api/v1/scalp/pdf/{report_id}...")
        pdf_response = client.get(f"/api/v1/scalp/pdf/{report_id}")
        assert pdf_response.status_code == 200
        assert pdf_response.headers.get("content-type") == "application/pdf"
        print(f"[OK] PDF generated successfully, size: {len(pdf_response.content)} bytes.")

def test_analyze_images():
    print("[TEST] Testing /api/v1/scalp/analyze-images with real/mock files...")
    
    import io
    from PIL import Image
    
    # Generate dummy in-memory JPEG for testing
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
        
    files = {
        "image_crown": ("crown.jpg", img_bytes, "image/jpeg"),
        "image_front": ("front.jpg", img_bytes, "image/jpeg"),
        "image_back": ("back.jpg", img_bytes, "image/jpeg")
    }
    api_key = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARNING] Skipping analyze-images AI endpoint test due to missing GEMINI_API_KEY.")
        return
    response = client.post("/api/v1/scalp/analyze-images", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "redness" in data
    assert "dead_skin" in data
    assert "sebum" in data
    assert "hair_density" in data
    assert "hair_thickness" in data
    print("[OK] /api/v1/scalp/analyze-images executed successfully.")
    print(f"     Results: {data}")

if __name__ == "__main__":
    print("--- Starting Automated API Tests ---")
    try:
        test_partners_endpoint()
        test_history_endpoint()
        test_safety_filter()
        test_diagnose_endpoint()
        test_analyze_images()
        print("--- All tests completed successfully! ---")
        sys.exit(0)
    except AssertionError as ae:
        print(f"[FAIL] Test assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Test failed with error: {e}")
        sys.exit(1)
