"""
정책 테이블을 PNG로 렌더링
행동근거 열을 제거한 버전
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
try:
    # Windows 시스템 한글 폰트 찾기
    font_path = r'C:\Windows\Fonts\malgun.ttf'  # 맑은 고딕
    if not __import__('os').path.exists(font_path):
        font_path = r'C:\Windows\Fonts\batang.ttf'  # 바탕
    if __import__('os').path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = 'Malgun Gothic'
except:
    pass

# 표의 데이터 (행동근거 열 제거)
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

headers = ["공식정보", "AI위치", "service_risk_level", "action", "최종행동", "우선순위"]

# Figure 생성
fig, ax = plt.subplots(figsize=(16, 12), dpi=100)
ax.axis('tight')
ax.axis('off')

# 테이블 생성
table = ax.table(cellText=data, colLabels=headers, cellLoc='center', loc='center',
                colWidths=[0.12, 0.12, 0.15, 0.12, 0.12, 0.08])

table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 2.5)

# 헤더 스타일
for i in range(len(headers)):
    table[(0, i)].set_facecolor('#4472C4')
    table[(0, i)].set_text_props(weight='bold', color='white')

# 데이터 행 스타일
for i in range(1, len(data) + 1):
    for j in range(len(headers)):
        cell = table[(i, j)]
        
        # 우선순위가 낮을수록 (숫자가 작을수록) 색이 더 진함
        priority = int(data[i-1][-1].split('/')[0])  # 첫 번째 우선순위 값
        
        if priority <= 2:
            cell.set_facecolor('#FFD966')  # 노랑 - 매우 높음
        elif priority <= 4:
            cell.set_facecolor('#FFC7CE')  # 연한 빨강 - 높음
        elif priority <= 6:
            cell.set_facecolor('#FFF2CC')  # 더 연한 노랑 - 중간
        else:
            cell.set_facecolor('#E2EFDA')  # 연한 초록 - 낮음
        
        # 특정 행 강조 (대피지시, 고립 신고, 지하+현장징후)
        if i in [11, 12, 13]:  # 대피지시, 고립신고, 지하+현장징후
            cell.set_facecolor('#FF6B6B')
            cell.set_text_props(weight='bold', color='white')
        
        # 실외 EVACUATE 강조
        if '실외' in str(data[i-1][2]) and 'EVACUATE' in str(data[i-1][3]):
            cell.set_text_props(weight='bold')
        
        cell.set_text_props(fontsize=8, family='DejaVu Sans')

plt.title('마른길 정책 결정 테이블 (2022년 8월 8일 기준)', 
          fontsize=14, weight='bold', pad=20)

plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

# PNG로 저장
output_path = r'c:\2026_Mareungil\diagrams\policy_decision_table.png'
plt.savefig(output_path, dpi=100, bbox_inches='tight', facecolor='white')
print(f"✓ 테이블이 저장되었습니다: {output_path}")
plt.close()
