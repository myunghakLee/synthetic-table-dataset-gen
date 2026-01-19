"""폰트 추출 및 적용 테스트"""
import re
from typing import Optional

DEFAULT_KOREAN_FONTS = (
    "'Malgun Gothic', '맑은 고딕', "
    "'Apple SD Gothic Neo', "
    "'Noto Sans KR', "
    "'NanumGothic', '나눔고딕', "
    "'Dotum', '돋움', "
    "'Gulim', '굴림', "
    "sans-serif"
)

def extract_font_family_from_html(html_content: str) -> Optional[str]:
    """HTML에서 font-family 추출"""
    patterns = [
        r"font-family\s*:\s*([^;}{]+)[;}]",
        r"font-family\s*=\s*['\"]([^'\"]+)['\"]",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            font_family = matches[0].strip().replace('"', "'").strip()
            if font_family:
                return font_family
    
    return None


# 테스트
html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <style>
        body {
            font-family: 'Malgun Gothic', '맑은 고딕', 'Apple SD Gothic Neo', sans-serif;
        }
    </style>
</head>
<body>
    <table><tr><td>테스트</td></tr></table>
</body>
</html>
"""

font = extract_font_family_from_html(html)
print(f"Extracted font: {font}")
print(f"Full font stack: {font}, {DEFAULT_KOREAN_FONTS}" if font else f"Default: {DEFAULT_KOREAN_FONTS}")
