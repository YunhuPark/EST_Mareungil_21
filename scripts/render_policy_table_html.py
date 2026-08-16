"""
정책 테이블을 HTML로 생성한 후 PNG로 스크린샷
"""
import subprocess
import tempfile
import os

html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>마른길 정책 결정 테이블</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif;
            background-color: white;
            padding: 40px;
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            font-size: 24px;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        th {
            background-color: #4472C4;
            color: white;
            padding: 12px;
            text-align: center;
            font-weight: bold;
            border: 1px solid #333;
            font-size: 13px;
        }
        td {
            padding: 10px 8px;
            text-align: center;
            border: 1px solid #999;
            font-size: 12px;
            min-height: 40px;
            vertical-align: middle;
        }
        tr:nth-child(even) td {
            background-color: #f9f9f9;
        }
        /* 행동근거 없는 일반 행들 */
        tbody tr:nth-child(1) td,
        tbody tr:nth-child(2) td,
        tbody tr:nth-child(3) td,
        tbody tr:nth-child(4) td,
        tbody tr:nth-child(5) td,
        tbody tr:nth-child(6) td,
        tbody tr:nth-child(7) td,
        tbody tr:nth-child(8) td,
        tbody tr:nth-child(9) td,
        tbody tr:nth-child(10) td,
        tbody tr:nth-child(11) td,
        tbody tr:nth-child(14) td,
        tbody tr:nth-child(15) td {
            background-color: #E2EFDA;
        }
        /* 우선순위 4-6 노란색 */
        tbody tr:nth-child(3) td,
        tbody tr:nth-child(6) td,
        tbody tr:nth-child(11) td {
            background-color: #FFF2CC;
        }
        /* 우선순위 1-2 빨강 (대피지시, 고립신고, 지하+현장징후) */
        tbody tr:nth-child(12) td,
        tbody tr:nth-child(13) td,
        tbody tr:nth-child(14) td {
            background-color: #FF6B6B;
            color: white;
            font-weight: bold;
        }
        .highlight-evacuate {
            font-weight: bold;
            color: #d00;
        }
        .data-unavailable {
            font-weight: bold;
            color: #d00;
        }
    </style>
</head>
<body>
    <h1>마른길 정책 결정 테이블 (2022년 8월 8일 기준)</h1>
    <table>
        <thead>
            <tr>
                <th>공식정보</th>
                <th>AI위치</th>
                <th>service_risk_level</th>
                <th>action</th>
                <th>최종행동</th>
                <th>우선순위</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>부재</td>
                <td>LOW</td>
                <td>실내·실외·지하</td>
                <td>SAFE</td>
                <td>MOVE</td>
                <td>10</td>
            </tr>
            <tr>
                <td>부재</td>
                <td>HIGH<br>(단독)</td>
                <td>실내</td>
                <td>CAUTION</td>
                <td>WAIT</td>
                <td>7</td>
            </tr>
            <tr>
                <td>부재</td>
                <td>HIGH<br>(단독)</td>
                <td>실외</td>
                <td>CAUTION</td>
                <td><span class="highlight-evacuate">EVACUATE</span></td>
                <td>6</td>
            </tr>
            <tr>
                <td>부재</td>
                <td>HIGH<br>(단독)</td>
                <td>지하</td>
                <td>CAUTION</td>
                <td>WAIT</td>
                <td>8</td>
            </tr>
            <tr>
                <td>부재</td>
                <td>HIGH<br>+ 추가신호</td>
                <td>실내</td>
                <td>DANGER</td>
                <td>WAIT</td>
                <td>7</td>
            </tr>
            <tr>
                <td>부재</td>
                <td>HIGH<br>+ 추가신호</td>
                <td>실외</td>
                <td>DANGER</td>
                <td><span class="highlight-evacuate">EVACUATE</span></td>
                <td>6</td>
            </tr>
            <tr>
                <td>부재</td>
                <td>HIGH<br>+ 추가신호</td>
                <td>지하</td>
                <td>DANGER</td>
                <td>WAIT</td>
                <td>8</td>
            </tr>
            <tr>
                <td>지연<br>(30분 초과)</td>
                <td>LOW</td>
                <td>실내·실외·지하</td>
                <td>CAUTION</td>
                <td>WAIT</td>
                <td>9</td>
            </tr>
            <tr>
                <td>지연<br>(30분 초과)</td>
                <td>HIGH</td>
                <td>실내/실외/지하</td>
                <td>CAUTION/<br>EVACUATE/<br>WAIT</td>
                <td>실내/실외/지하</td>
                <td>7/6/8</td>
            </tr>
            <tr>
                <td>지연<br>(30분 초과)</td>
                <td>HIGH<br>+ 추가신호</td>
                <td>실내/실외/지하</td>
                <td>DANGER/<br>EVACUATE/<br>WAIT</td>
                <td>실내/실외/지하</td>
                <td>7/6/8</td>
            </tr>
            <tr>
                <td><strong>대피지시</strong></td>
                <td>LOW·HIGH<br>·산출불가</td>
                <td>실내·실외·지하</td>
                <td><strong>SEVERE</strong></td>
                <td><strong>EVACUATE</strong></td>
                <td>4</td>
            </tr>
            <tr>
                <td><strong>고립 신고</strong></td>
                <td>무관</td>
                <td>무관</td>
                <td><strong>SEVERE</strong></td>
                <td><strong>EMERGENCY</strong></td>
                <td>1</td>
            </tr>
            <tr>
                <td><strong>지하 +<br>현장 징후</strong></td>
                <td>무관</td>
                <td>지하</td>
                <td><strong>SEVERE</strong></td>
                <td><strong>EVACUATE</strong></td>
                <td>2</td>
            </tr>
            <tr>
                <td>AI 산출불가<br>+ 강우자료 있음</td>
                <td>null</td>
                <td>실내·실외·지하</td>
                <td>CAUTION</td>
                <td>MOVE</td>
                <td>10</td>
            </tr>
            <tr>
                <td>AI 산출불가<br>+ 강우자료 없음</td>
                <td>null</td>
                <td>실내·실외·지하</td>
                <td>CAUTION</td>
                <td><span class="data-unavailable">UNAVAILABLE</span></td>
                <td>5</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

# 임시 HTML 파일 생성
with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
    f.write(html_content)
    html_file = f.name

try:
    # Playwright로 PNG 생성
    output_path = r'c:\2026_Mareungil\diagrams\policy_decision_table.png'
    
    # Playwright 스크립트
    script = f"""
const {{ chromium }} = require('playwright');

(async () => {{
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto('file:///{html_file.replace(chr(92), "/")}');
    await page.waitForTimeout(1000);
    await page.screenshot({{ path: '{output_path.replace(chr(92), "/")}' }});
    await browser.close();
}})();
"""
    
    # Node.js가 없으면 다른 방법 사용
    try:
        result = subprocess.run(['npm', 'list', 'playwright'], 
                              capture_output=True, text=True, cwd=r'c:\2026_Mareungil')
        if result.returncode == 0:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as js_f:
                js_f.write(script)
                js_file = js_f.name
            subprocess.run(['node', js_file], cwd=r'c:\2026_Mareungil')
            os.unlink(js_file)
        else:
            raise Exception("Playwright not found")
    except:
        # Playwright 대신 PIL 사용해서 HTML을 이미지로 변환
        # wkhtmltoimage 또는 다른 방법 필요
        print("⚠ Playwright 또는 wkhtmltoimage를 사용할 수 없습니다.")
        print("  대신 HTML 파일을 저장합니다.")
        with open(r'c:\2026_Mareungil\diagrams\policy_decision_table.html', 'w', encoding='utf-8') as hf:
            hf.write(html_content)
        print(f"✓ HTML 파일이 저장되었습니다: c:\\2026_Mareungil\\diagrams\\policy_decision_table.html")
        
finally:
    os.unlink(html_file)
