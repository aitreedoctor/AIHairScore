import os
import sqlite3
import json
from fastapi import APIRouter, HTTPException, responses
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .db import get_db_connection

router = APIRouter()

# Directory configuration
PDF_DIR = os.path.join(os.path.dirname(__file__), "static", "pdf")
os.makedirs(PDF_DIR, exist_ok=True)

# Register Korean Font (Malgun Gothic from Windows System)
FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

try:
    font_path = "C:\\Windows\\Fonts\\malgun.ttf"
    font_path_bold = "C:\\Windows\\Fonts\\malgunbd.ttf"
    
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("Malgun", font_path))
        FONT_NAME = "Malgun"
        if os.path.exists(font_path_bold):
            pdfmetrics.registerFont(TTFont("Malgun-Bold", font_path_bold))
            FONT_BOLD = "Malgun-Bold"
        else:
            FONT_BOLD = "Malgun"
    else:
        # Fallback fonts if not Windows default
        fallback_paths = [
            ("C:\\Windows\\Fonts\\batang.ttc", "Batang"),
            ("C:\\Windows\\Fonts\\gulim.ttc", "Gulim")
        ]
        for path, name in fallback_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                FONT_NAME = name
                FONT_BOLD = name
                break
except Exception as e:
    print(f"[PDF Service] Font registration failed, using default Helvetica: {e}")

@router.get("/pdf/{report_id}")
async def generate_pdf_report(report_id: str):
    """
    Generates a premium, structured PDF report for the given scalp report ID.
    Returns the file response.
    """
    # Fetch report from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scalp_reports WHERE id = ?", (report_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
        
    report = dict(row)
    symptoms = json.loads(report["subjective_symptoms"])
    
    # PDF File Path
    pdf_filename = f"scalp_report_{report_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    
    try:
        # Create Document (A4 size with compact margins for 1-page fit if possible)
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom Typography
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#4C1D95"), # Deep purple
            alignment=1, # Center
            spaceAfter=15
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            fontName=FONT_NAME,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6B7280"), # Muted gray
            alignment=1,
            spaceAfter=25
        )
        
        section_heading = ParagraphStyle(
            'SectionHeading',
            fontName=FONT_BOLD,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=12,
            spaceAfter=6
        )
        
        body_style = ParagraphStyle(
            'ReportBody',
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#374151")
        )
        
        bullet_style = ParagraphStyle(
            'ReportBullet',
            parent=body_style,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4
        )
        
        disclaimer_style = ParagraphStyle(
            'ReportDisclaimer',
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#9CA3AF"),
            alignment=1,
            spaceBefore=20
        )
        
        table_header_style = ParagraphStyle(
            'TableHeader',
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=12,
            textColor=colors.white,
            alignment=1
        )
        
        table_cell_style = ParagraphStyle(
            'TableCell',
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=1
        )
        
        table_cell_left = ParagraphStyle(
            'TableCellLeft',
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=0
        )
        
        story = []
        
        # 1. Header Title
        story.append(Paragraph(f"{report['user_id']}님의 두피 지문 분석 및 전용 케어 제안서", title_style))
        story.append(Paragraph(f"분석 일시: {report['created_at']}  |  발행 번호: {report['id'][:18]}...", subtitle_style))
        
        # 2. User Info Block (Table)
        info_data = [
            [
                Paragraph("<b>연령</b>", table_cell_style), 
                Paragraph(f"{report['age']} 세", table_cell_style),
                Paragraph("<b>성별</b>", table_cell_style), 
                Paragraph("남성" if report['gender'].lower() == "male" else "여성", table_cell_style)
            ],
            [
                Paragraph("<b>가족력</b>", table_cell_style), 
                Paragraph("있음" if report['family_history'] != "none" else "없음", table_cell_style),
                Paragraph("<b>분석 지역</b>", table_cell_style), 
                Paragraph(report['location'], table_cell_style)
            ],
            [
                Paragraph("<b>자각 증상</b>", table_cell_style), 
                Paragraph(", ".join(symptoms) if symptoms else "없음", table_cell_left),
                Paragraph("", table_cell_style),
                Paragraph("", table_cell_style)
            ]
        ]
        
        info_table = Table(info_data, colWidths=[80, 170, 80, 175])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,2), colors.HexColor("#F3F4F6")),
            ('BACKGROUND', (2,0), (2,1), colors.HexColor("#F3F4F6")),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#1F2937")),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ('SPAN', (1,2), (3,2)), # Span subjective symptoms across
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 15))
        
        # 3. Comprehensive Score Block
        score_bg_color = "#EEF2F6"
        score_text_color = "#10B981" # Green
        if report['overall_score'] < 50:
            score_bg_color = "#FEF2F2"
            score_text_color = "#EF4444" # Red
        elif report['overall_score'] < 80:
            score_bg_color = "#FFFBEB"
            score_text_color = "#F59E0B" # Yellow
            
        score_html = f"<font size='14' color='{score_text_color}'><b>{report['overall_score']}점 ({report['overall_grade']})</b></font>"
        score_paragraph = Paragraph(f"현재 {report['user_id']}님의 두피 환경 종합 지수는 {score_html} 입니다.", body_style)
        
        score_table_data = [[score_paragraph]]
        score_table = Table(score_table_data, colWidths=[505])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(score_bg_color)),
            ('PADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 15))
        
        # 4. Visual Analysis Score Matrix (Table)
        def get_bar_text(val):
            # val is 0 to 3
            level_names = ["양호 (0)", "주의 (1)", "경고 (2)", "위험 (3)"]
            colors_list = ["#10B981", "#F59E0B", "#EF4444", "#DC2626"]
            color = colors_list[min(3, max(0, val))]
            name = level_names[min(3, max(0, val))]
            return f"<font color='{color}'><b>{name}</b></font>"

        metric_data = [
            [
                Paragraph("<b>비전 분석 항목</b>", table_header_style), 
                Paragraph("<b>정상 기준</b>", table_header_style), 
                Paragraph("<b>내 분석 수준</b>", table_header_style), 
                Paragraph("<b>임상 가이드라인 요약</b>", table_header_style)
            ],
            [
                Paragraph("두피 홍반 (붉은기)", table_cell_style), 
                Paragraph("<font color='#10B981'><b>양호 (0)</b></font>", table_cell_style),
                Paragraph(get_bar_text(report['redness']), table_cell_style),
                Paragraph("두피 모세혈관 확장성 및 피부 민감도 자극 수준", table_cell_left)
            ],
            [
                Paragraph("두피 각질", table_cell_style), 
                Paragraph("<font color='#10B981'><b>양호 (0)</b></font>", table_cell_style),
                Paragraph(get_bar_text(report['dead_skin']), table_cell_style),
                Paragraph("피부 턴오버 주기 불안정 및 수분 부족 각질량", table_cell_left)
            ],
            [
                Paragraph("두피 피지 (유분량)", table_cell_style), 
                Paragraph("<font color='#10B981'><b>양호 (0)</b></font>", table_cell_style),
                Paragraph(get_bar_text(report['sebum']), table_cell_style),
                Paragraph("모공 주변 유분 과다 과각화 및 모근 질식 환경 지수", table_cell_left)
            ],
            [
                Paragraph("모발 밀도", table_cell_style), 
                Paragraph("<font color='#10B981'><b>풍성 (3)</b></font>", table_cell_style),
                Paragraph(get_bar_text(report['hair_density']), table_cell_style),
                Paragraph("모낭 당 평균 머리카락 개수 및 모근 분포 밀집도", table_cell_left)
            ],
            [
                Paragraph("모발 굵기", table_cell_style), 
                Paragraph("<font color='#10B981'><b>굵음 (3)</b></font>", table_cell_style),
                Paragraph(get_bar_text(report['hair_thickness']), table_cell_style),
                Paragraph("모낭 영양 공급 장애에 의한 모발 연모화 진행 상태", table_cell_left)
            ],
        ]
        
        metric_table = Table(metric_data, colWidths=[110, 80, 80, 235])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4C1D95")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(metric_table)
        story.append(Spacer(1, 15))
        
        # 5. Detailed AI Opinion & Recommendations
        story.append(Paragraph("1. AI 맞춤형 종합 가이드 분석 의견", section_heading))
        story.append(Paragraph(report['ai_opinion'], body_style))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("2. 초개인화 홈케어 솔루션 가이드", section_heading))
        # Convert simple markdown bullet points to reportlab paragraphs
        solution_lines = report['homecare_solution'].split('\n')
        for line in solution_lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('*') or line.startswith('-'):
                # Format bullet points
                cleaned_line = line.lstrip('* -').strip()
                story.append(Paragraph(f"• {cleaned_line}", bullet_style))
            else:
                story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("3. 전문가 웰니스 검사 제안 & 제휴처 안내", section_heading))
        story.append(Paragraph(report['offline_proposal'], body_style))
        story.append(Spacer(1, 20))
        
        # 6. Medical Disclaimer (Footer)
        story.append(Paragraph(
            "<b>[의료법 제27조 준수 안내]</b><br/>"
            "본 분석 결과지는 의학적 상태를 진단하거나 의약품을 처방하는 의사의 공식 진단서를 대체할 수 없습니다. "
            "추정 수치 및 케어 루틴은 비전 AI 통계 모델을 바탕으로 한 자가 모니터링 웰니스 가이드라인이므로, "
            "정밀한 의학적 검사 및 질환 감별은 피부과 전문의 또는 모발 의학 전문가와의 대면 검진을 요합니다.",
            disclaimer_style
        ))
        
        # Build Document
        doc.build(story)
        
        return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_filename)
        
    except Exception as e:
        print(f"[PDF Generation Error] {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
