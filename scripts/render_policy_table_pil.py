"""
정책 테이블을 PIL로 PNG로 생성 (한글 지원)
"""
from PIL import Image, ImageDraw, ImageFont
import os

# 테이블 데이터
headers = ["공식정보", "AI위치", "service_risk_level", "action", "최종행동", "우선순위"]
data = [
    ["부재", "LOW", "실내·실외·지하", "SAFE", "MOVE", "10"],
    ["부재", "HIGH\n(단독)", "실내", "CAUTION", "WAIT", "7"],
    ["부재", "HIGH\n(단독)", "실외", "CAUTION", "EVACUATE", "6"],
    ["부재", "HIGH\n(단독)", "지하", "CAUTION", "WAIT", "8"],
    ["부재", "HIGH\n+ 추가신호", "실내", "DANGER", "WAIT", "7"],
    ["부재", "HIGH\n+ 추가신호", "실외", "DANGER", "EVACUATE", "6"],
    ["부재", "HIGH\n+ 추가신호", "지하", "DANGER", "WAIT", "8"],
    ["지연\n(30분 초과)", "LOW", "실내·실외·지하", "CAUTION", "WAIT", "9"],
    ["지연\n(30분 초과)", "HIGH", "실내/실외/지하", "CAUTION/\nEVACUATE/\nWAIT", "실내/실외/지하", "7/6/8"],
    ["지연\n(30분 초과)", "HIGH\n+ 추가신호", "실내/실외/지하", "DANGER/\nEVACUATE/\nWAIT", "실내/실외/지하", "7/6/8"],
    ["대피지시", "LOW·HIGH\n·산출불가", "실내·실외·지하", "SEVERE", "EVACUATE", "4"],
    ["고립 신고", "무관", "무관", "SEVERE", "EMERGENCY", "1"],
    ["지하 +\n현장 징후", "무관", "지하", "SEVERE", "EVACUATE", "2"],
    ["AI 산출불가\n+ 강우자료 있음", "null", "실내·실외·지하", "CAUTION", "MOVE", "10"],
    ["AI 산출불가\n+ 강우자료 없음", "null", "실내·실외·지하", "CAUTION", "UNAVAILABLE", "5"],
]

# 폰트 로드
try:
    font_path = r'C:\Windows\Fonts\malgun.ttf'  # 맑은 고딕
    if not os.path.exists(font_path):
        font_path = r'C:\Windows\Fonts\gulim.ttf'  # 굴림
    font = ImageFont.truetype(font_path, 11)
    font_header = ImageFont.truetype(font_path, 12)
    font_title = ImageFont.truetype(font_path, 18)
except:
    font = ImageFont.load_default()
    font_header = font
    font_title = font

# 셀 너비와 높이 설정
col_widths = [110, 100, 150, 110, 110, 80]
row_height = 50
header_height = 50
margin = 30

# 계산
total_width = sum(col_widths) + 2
total_height = header_height + (len(data) * row_height) + (2 * margin) + 60  # 제목 60px

# 이미지 생성
img = Image.new('RGB', (total_width + 2 * margin, total_height), color='white')
draw = ImageDraw.Draw(img)

# 제목 그리기
title = "마른길 정책 결정 테이블 (2022년 8월 8일 기준)"
title_bbox = draw.textbbox((0, 0), title, font=font_title)
title_width = title_bbox[2] - title_bbox[0]
title_x = (total_width + 2 * margin - title_width) // 2
draw.text((title_x, 10), title, fill='black', font=font_title)

# 시작 위치
start_y = 70

# 색상 정의
header_color = '#4472C4'
safe_color = '#E2EFDA'
medium_color = '#FFF2CC'
danger_color = '#FF6B6B'
border_color = '#999999'
text_white = 'white'
text_black = 'black'

# 헤더 그리기
x = margin
y = start_y
for i, header in enumerate(headers):
    # 배경
    draw.rectangle(
        [x, y, x + col_widths[i], y + header_height],
        fill=header_color,
        outline=border_color,
        width=1
    )
    # 텍스트
    text_bbox = draw.textbbox((0, 0), header, font=font_header)
    text_height = text_bbox[3] - text_bbox[1]
    text_x = x + (col_widths[i] - (text_bbox[2] - text_bbox[0])) // 2
    text_y = y + (header_height - text_height) // 2
    draw.text((text_x, text_y), header, fill=text_white, font=font_header)
    x += col_widths[i]

# 데이터 행 그리기
y = start_y + header_height
for row_idx, row in enumerate(data):
    x = margin
    
    # 행의 배경색 결정
    if row_idx in [10, 11, 12]:  # 대피지시, 고립신고, 지하+현장징후
        bg_color = danger_color
        text_color = text_white
    elif row_idx in [2, 5, 10]:  # 우선순위 6 (빨강 기울임)
        bg_color = medium_color
        text_color = text_black
    else:
        bg_color = safe_color
        text_color = text_black
    
    # 각 셀 그리기
    for col_idx, cell_text in enumerate(row):
        # 배경
        draw.rectangle(
            [x, y, x + col_widths[col_idx], y + row_height],
            fill=bg_color,
            outline=border_color,
            width=1
        )
        
        # 텍스트 그리기 (멀티라인 지원)
        lines = cell_text.split('\n')
        line_height = 15
        total_text_height = len(lines) * line_height
        start_text_y = y + (row_height - total_text_height) // 2
        
        for line_idx, line in enumerate(lines):
            text_bbox = draw.textbbox((0, 0), line, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = x + (col_widths[col_idx] - text_width) // 2
            text_y = start_text_y + (line_idx * line_height)
            draw.text((text_x, text_y), line, fill=text_color, font=font)
        
        x += col_widths[col_idx]
    
    y += row_height

# 저장
output_path = r'c:\2026_Mareungil\diagrams\policy_decision_table.png'
img.save(output_path, 'PNG', quality=95)
print(f"✓ 테이블이 저장되었습니다: {output_path}")
