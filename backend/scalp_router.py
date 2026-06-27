import uuid
import json
import os
import random
import re
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional, Dict
from PIL import Image
import io

from google import genai
from google.genai import types

from .db import get_db_connection

router = APIRouter()

# Forbidden words filter rules (Medical Law Art 27 compliance)
FORBIDDEN_REPLACEMENTS = {
    r"진단": "상태 분석",
    r"처방": "관리 추천",
    r"탈모증": "탈모 경향성",
    r"치료": "개선 관리",
    r"확진": "판독 완료",
    r"(?<!주의)(?<!주)의사(?!결정|소통|항)": "케어 가이드",
    r"약처방": "케어 제안"
}

def apply_safety_filter(text: str) -> str:
    """
    Applies regex replacement on forbidden words to ensure legal compliance.
    """
    filtered_text = text
    for pattern, replacement in FORBIDDEN_REPLACEMENTS.items():
        # Case insensitive regex replacement
        filtered_text = re.sub(pattern, replacement, filtered_text)
    return filtered_text

class VisionAnalysis(BaseModel):
    redness: int
    dead_skin: int
    sebum: int
    hair_density: int
    hair_thickness: int

class UserSurvey(BaseModel):
    age: int
    gender: str
    family_history: str
    subjective_symptoms: List[str]

class DiagnoseRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    vision_analysis: VisionAnalysis
    user_survey: UserSurvey
    location: str

def get_gemini_client():
    api_keys_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_keys_env:
        raise HTTPException(status_code=500, detail="Gemini API Key is not set in backend environment.")
    keys = [k.strip() for k in api_keys_env.split(",") if k.strip()]
    if not keys:
        raise HTTPException(status_code=500, detail="No valid Gemini API Keys found.")
    api_key = random.choice(keys)
    return genai.Client(api_key=api_key)

@router.post("/analyze-image")
async def analyze_image(image: UploadFile = File(...)):
    """
    Receives scalp image, sends it to Gemini Vision API,
    estimates scores (0-3) for Redness, Dead Skin, Sebum, Density, Thickness,
    and returns them in a structured JSON.
    """
    # Verify file type
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")
    
    try:
        image_content = await image.read()
        image_part = types.Part.from_bytes(data=image_content, mime_type=image.content_type)
        
        client = get_gemini_client()
        
        prompt = """
        You are a professional scalp vision analyzer. Analyze the uploaded scalp image and estimate scores (integer 0, 1, 2, or 3) for the following 5 metrics:
        1. redness (홍반 - redness/irritation of the scalp. 0: healthy, 1: mild, 2: warning, 3: severe)
        2. dead_skin (각질 - dead skin cells/dandruff. 0: clean, 1: mild, 2: warning, 3: severe flakes)
        3. sebum (피지 - oiliness/sebum level. 0: dry/normal, 1: mild oil, 2: warning oily, 3: severe sebum overflow)
        4. hair_density (모발밀도 - density of hair follicles. 3: thick density/healthy, 2: average density, 1: warning sparse, 0: severe sparse hair)
        5. hair_thickness (모발굵기 - thickness of hair strands. 3: healthy thick, 2: average, 1: warning thinning, 0: severe thinning)

        Ensure you analyze the image objectively.
        You must return ONLY a valid JSON object matching the schema below. Do not include markdown formatting (like ```json), just raw JSON.
        {
          "redness": <0-3>,
          "dead_skin": <0-3>,
          "sebum": <0-3>,
          "hair_density": <0-3>,
          "hair_thickness": <0-3>
        }
        """
        
        # Call Gemini model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        
        res_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(res_text)
        
        # Validate returned fields
        required_fields = ["redness", "dead_skin", "sebum", "hair_density", "hair_thickness"]
        for f in required_fields:
            if f not in data:
                data[f] = 1 # default fallback
            else:
                # clamp values between 0 and 3
                data[f] = max(0, min(3, int(data[f])))
                
        return data
        
    except json.JSONDecodeError as je:
        print(f"[JSON Decode Error] Gemini response: {response.text if 'response' in locals() else ''}")
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(je)}")
    except Exception as e:
        print(f"[Image Analysis Error] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")

@router.post("/analyze-images")
async def analyze_images(
    image_crown: Optional[UploadFile] = File(None),
    image_front: Optional[UploadFile] = File(None),
    image_parting: Optional[UploadFile] = File(None),
    image_left_front: Optional[UploadFile] = File(None),
    image_right_front: Optional[UploadFile] = File(None),
    image_back: Optional[UploadFile] = File(None)
):
    """
    Receives up to 6 scalp images from different zones, sends them to Gemini Vision API,
    estimates scores (0-3) for Redness, Dead Skin, Sebum, Density, Thickness by comparing them,
    and returns them in a structured JSON.
    """
    client = get_gemini_client()
    contents = []
    
    prompt = """
    You are a professional scalp vision analyzer. You are provided with scalp images from different zones of the same user.
    Identify the uploaded images in this order (if provided):
    1. image_crown: Crown/가마 (정수리) area (usually has O-shape sebum, dead skin, and density symptoms)
    2. image_front: Front/이마 (앞머리/헤어라인) area (checking front hairline recession and forehead density)
    3. image_parting: Center Parting (중앙 가르마) area (linear hair parting expansion tracking)
    4. image_left_front: Left M-line (좌측 M자 헤어라인) area (45-degree angle profile checking front line recession)
    5. image_right_front: Right M-line (우측 M자 헤어라인) area (45-degree angle profile checking front line recession)
    6. image_back: Back/Occipital (측두부/후두부) area (which serves as the baseline/control area, where hair is thickest and healthy, unaffected by androgenic hair loss receptors)

    Analyze these images and calculate general scores (integer 0, 1, 2, or 3) for the user's overall scalp condition.
    Important: Use the Back area (image_back, if provided) as the baseline (thickness: 3, density: 3). Compare the Crown (1st) and Front/Parting/M-lines against this baseline to check for thinning (hair_thickness) and hair loss (hair_density).
    
    Estimate scores for the following 5 metrics:
    1. redness (홍반 - redness/irritation. 0: healthy, 1: mild, 2: warning, 3: severe)
    2. dead_skin (각질 - dead skin cells/dandruff. 0: clean, 1: mild, 2: warning, 3: severe flakes)
    3. sebum (피지 - oiliness/sebum level. 0: dry/normal, 1: mild, 2: warning, 3: severe)
    4. hair_density (모발밀도 - density. 3: thick/healthy, 2: average, 1: warning sparse, 0: severe sparse hair)
    5. hair_thickness (모발굵기 - thickness. 3: healthy thick, 2: average, 1: warning thinning, 0: severe thinning)

    Ensure you analyze the images objectively.
    You must return ONLY a valid JSON object matching the schema below. Do not include markdown formatting (like ```json), just raw JSON.
    {
      "redness": <0-3>,
      "dead_skin": <0-3>,
      "sebum": <0-3>,
      "hair_density": <0-3>,
      "hair_thickness": <0-3>
    }
    """
    contents.append(prompt)
    
    has_images = False
    for img_file in [image_crown, image_front, image_parting, image_left_front, image_right_front, image_back]:
        if img_file and img_file.filename:
            content_type = img_file.content_type or "image/jpeg"
            img_content = await img_file.read()
            if len(img_content) > 0:
                img_part = types.Part.from_bytes(data=img_content, mime_type=content_type)
                contents.append(img_part)
                has_images = True
                
    if not has_images:
        return {
            "redness": 1,
            "dead_skin": 1,
            "sebum": 1,
            "hair_density": 2,
            "hair_thickness": 2
        }
        
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        res_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(res_text)
        
        # Validate returned fields
        required_fields = ["redness", "dead_skin", "sebum", "hair_density", "hair_thickness"]
        for f in required_fields:
            if f not in data:
                data[f] = 1 # default fallback
            else:
                data[f] = max(0, min(3, int(data[f])))
                
        return data
    except Exception as e:
        print(f"[Multi-Image Analysis Error] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Multi-image analysis failed: {str(e)}")

@router.post("/diagnose")
async def diagnose(payload: DiagnoseRequest):
    """
    Generates a scalp wellness care report based on vision scores and survey data.
    Enforces strict South Korean medical law compliance (Anti-Hallucination temperature + post regex filter).
    """
    try:
        client = get_gemini_client()
        
        system_instruction = """
        # [Role & Identity]
        You are 'AI Hair Score', an advanced AI visual analyzer and wellness care curator specializing in human scalp and hair health. Your goal is to analyze quantitative data from vision AI and user surveys to provide highly professional, personalized, and motivating holistic care routines.

        # [Strict Legal Guardrails (South Korean Medical Law - Article 27)]
        You are NOT a medical doctor. You CANNOT diagnose medical conditions or prescribe medical treatments/pharmaceuticals. To strictly comply with the law, you must adhere to the following linguistic rules:
        1. NEVER use diagnostic terms: Forbidden words include '탈모증(Alopecia)', '확진(Confirm)', '진단(Diagnosis)', '치료(Cure/Treatment)', '처방(Prescription)'.
        2. ALWAYS use wellness/care terms: Use '상태 분석(Status Analysis)', '모니터링(Monitoring)', '경향성/가능성(Tendency/Possibility)', '케어/관리(Care/Management)', '제안/추천(Suggestion/Recommendation)'.
        3. DO NOT prescribe prescription-only drugs (e.g., Finasteride, Minoxidil oral). You can only recommend Ministry of Food and Drug Safety (MFDS) approved functional cosmetics (shampoo, tonic, ampoule) and health supplements (Biotin, Beer yeast).
        4. ALWAYS append a medical disclaimer at the very end of the report.

        # [Input Data Structure]
        You will receive JSON data containing:
        1. `vision_analysis`: Scores (0-3) for Redness(홍반), DeadSkin(각질), Sebum(피지), HairDensity(모발밀도), HairThickness(모발굵기).
        2. `user_survey`: Age, Gender, Family History, Subjective Symptoms (Itching, Heat, Hair loss count).
        3. `location`: User's broad location for local care center matching.

        # [Output Report Structure & Tone]
        Generate the report in professional, encouraging, and data-driven Korean. Avoid dry textbook tones; sound like a premium private scalp-care specialist.
        Return a JSON object containing exactly these fields:
        {
          "overall_score": <Calculated overall health score 0-100 based on the 5 metrics where 100 is perfect and 0 is critical>,
          "overall_grade": "<Brief grade/status name, e.g., '지성 및 열성 장벽 약화 경향', '건강한 정상 두피', '건조성 각질 케어 필요' 등>",
          "ai_opinion": "<AI 종합 가이드 의견 - Detailed paragraph explain why these scores occurred in correlation to survey>",
          "homecare_solution": "<초개인화 홈케어 솔루션 - Specific functional ingredients & step-by-step daily behavior routine in markdown>",
          "offline_proposal": "<전문가 팁 및 정밀 확인 제안 - Suggesting visiting local care centers, emphasizing it is tracking guide, not medical diagnostic>"
        }
        Do not include markdown blocks like ```json in the output.
        """
        
        input_data = {
            "vision_analysis": {
                "redness": payload.vision_analysis.redness,
                "dead_skin": payload.vision_analysis.dead_skin,
                "sebum": payload.vision_analysis.sebum,
                "hair_density": payload.vision_analysis.hair_density,
                "hair_thickness": payload.vision_analysis.hair_thickness
            },
            "user_survey": {
                "age": payload.user_survey.age,
                "gender": payload.user_survey.gender,
                "family_history": payload.user_survey.family_history,
                "subjective_symptoms": payload.user_survey.subjective_symptoms
            },
            "location": payload.location
        }
        
        prompt = f"Please analyze this input data and return the JSON response:\n{json.dumps(input_data, ensure_ascii=False)}"
        
        # Call Gemini model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.2 # Lower temperature for anti-hallucination/strict legal compliance
            )
        )
        
        res_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(res_text)
        
        # Post-processing Safety Filter on textual content (Double Protection)
        data["ai_opinion"] = apply_safety_filter(data.get("ai_opinion", ""))
        data["homecare_solution"] = apply_safety_filter(data.get("homecare_solution", ""))
        data["offline_proposal"] = apply_safety_filter(data.get("offline_proposal", ""))
        data["overall_grade"] = apply_safety_filter(data.get("overall_grade", ""))
        
        # Calculate overall score if not provided or out of bounds
        overall_score = data.get("overall_score", 70)
        overall_score = max(0, min(100, int(overall_score)))
        
        report_id = str(uuid.uuid4())
        
        # Save to Database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO scalp_reports (
            id, user_id, age, gender, family_history, subjective_symptoms, location,
            redness, dead_skin, sebum, hair_density, hair_thickness,
            overall_score, overall_grade, ai_opinion, homecare_solution, offline_proposal,
            raw_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id,
            payload.user_id,
            payload.user_survey.age,
            payload.user_survey.gender,
            payload.user_survey.family_history,
            json.dumps(payload.user_survey.subjective_symptoms, ensure_ascii=False),
            payload.location,
            payload.vision_analysis.redness,
            payload.vision_analysis.dead_skin,
            payload.vision_analysis.sebum,
            payload.vision_analysis.hair_density,
            payload.vision_analysis.hair_thickness,
            overall_score,
            data.get("overall_grade", "두피 웰니스 관리 단계"),
            data.get("ai_opinion", ""),
            data.get("homecare_solution", ""),
            data.get("offline_proposal", ""),
            res_text
        ))
        conn.commit()
        conn.close()
        
        data["id"] = report_id
        data["user_id"] = payload.user_id
        data["age"] = payload.user_survey.age
        data["gender"] = payload.user_survey.gender
        data["location"] = payload.location
        data["family_history"] = payload.user_survey.family_history
        data["subjective_symptoms"] = payload.user_survey.subjective_symptoms
        data["redness"] = payload.vision_analysis.redness
        data["dead_skin"] = payload.vision_analysis.dead_skin
        data["sebum"] = payload.vision_analysis.sebum
        data["hair_density"] = payload.vision_analysis.hair_density
        data["hair_thickness"] = payload.vision_analysis.hair_thickness
        
        return data
        
    except json.JSONDecodeError as je:
        print(f"[JSON Decode Error] {res_text if 'res_text' in locals() else ''}")
        raise HTTPException(status_code=500, detail=f"AI returned invalid report JSON: {str(je)}")
    except Exception as e:
        print(f"[Diagnose Error] {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

@router.get("/history")
async def get_history(user_id: str = "default_user"):
    """
    Retrieves scalp reports history list.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_id == "all":
            cursor.execute("""
            SELECT id, overall_score, overall_grade, redness, dead_skin, sebum, hair_density, hair_thickness, age, gender, created_at
            FROM scalp_reports
            ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
            SELECT id, overall_score, overall_grade, redness, dead_skin, sebum, hair_density, hair_thickness, age, gender, created_at
            FROM scalp_reports
            WHERE user_id = ?
            ORDER BY created_at DESC
            """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@router.get("/report/{report_id}")
async def get_report(report_id: str):
    """
    Retrieves a single scalp report by ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scalp_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Report not found")
        
        data = dict(row)
        data["subjective_symptoms"] = json.loads(data["subjective_symptoms"])
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch report: {str(e)}")

@router.get("/partners")
async def get_partners(location: str = ""):
    """
    Returns scalp partners by location search.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clean and split location to search by district/city
        loc_query = f"%{location}%" if location else "%"
        cursor.execute("""
        SELECT name, category, address, phone, benefit
        FROM scalp_partners
        WHERE address LIKE ? OR name LIKE ?
        """, (loc_query, loc_query))
        rows = cursor.fetchall()
        
        # If no results found for location, fallback to all partners
        if not rows and location:
            cursor.execute("SELECT name, category, address, phone, benefit FROM scalp_partners")
            rows = cursor.fetchall()
            
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch partners: {str(e)}")

@router.post("/test-safety-filter")
async def test_safety_filter(text: str = Form(...)):
    """
    Admin playground testing endpoint to check if safety filtering is replacing forbidden words correctly.
    """
    filtered = apply_safety_filter(text)
    detected_violations = [word for word in ["진단", "처방", "탈모증", "치료", "확진", "의사", "약처방"] if word in text]
    return {
        "original": text,
        "filtered": filtered,
        "detected": detected_violations,
        "is_safe": len(detected_violations) == 0 or filtered != text
    }
