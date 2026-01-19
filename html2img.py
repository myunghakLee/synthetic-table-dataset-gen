import asyncio
import base64
import random
import glob
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from playwright.async_api import async_playwright


# -----------------------------
# 기본 한글 폰트 설정
# -----------------------------
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
    """
    HTML 내용에서 font-family CSS 속성을 추출합니다.
    
    Args:
        html_content: HTML 문자열
        
    Returns:
        추출된 font-family 값 또는 None
    """
    # CSS style 태그 내에서 font-family 찾기
    patterns = [
        r"font-family\s*:\s*([^;}{]+)[;}]",  # CSS 블록 내
        r"font-family\s*=\s*['\"]([^'\"]+)['\"]",  # inline style
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            # 첫 번째 매치 반환 (보통 body나 table에 적용된 폰트)
            font_family = matches[0].strip()
            # 따옴표 정리
            font_family = font_family.replace('"', "'").strip()
            if font_family:
                return font_family
    
    return None


# -----------------------------
# Helper: Clean markdown codeblocks
# -----------------------------
def clean_markdown_codeblocks(content: str) -> str:
    """
    HTML 내용에서 마크다운 코드블록(```html ... ```)을 제거합니다.
    """
    content = content.strip()
    
    # 마크다운 코드블록 제거
    if content.startswith("```"):
        lines = content.split("\n")
        # 첫 줄 (```html 등) 제거
        lines = lines[1:]
        # 마지막 줄 (```) 제거
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    
    return content.strip()


def remove_caption_tags(content: str) -> str:
    """
    HTML 내용에서 <caption>...</caption> 태그를 제거합니다.
    """
    import re
    # <caption>...</caption> 태그 전체 제거 (줄바꿈 포함)
    content = re.sub(r'<caption[^>]*>.*?</caption>\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
    return content


# -----------------------------
# Helper: Random Pastel Color
# -----------------------------
def get_random_pastel_color() -> str:
    """배경으로 사용할 매우 옅은 파스텔톤 색상을 랜덤 생성합니다."""
    # R, G, B 값을 매우 높게(240~255) 설정하여 매우 밝은 색 생성
    r = random.randint(240, 255)
    g = random.randint(240, 255)
    b = random.randint(240, 255)
    return f"#{r:02x}{g:02x}{b:02x}"


# -----------------------------
# Font injection (base64)
# -----------------------------
def font_face_base64(font_path: str, family: str = "MyKR") -> str:
    fp = Path(font_path).resolve()
    if not fp.exists():
        raise FileNotFoundError(f"Font file not found: {fp}")

    data = fp.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")

    ext = fp.suffix.lower()
    if ext == ".ttf":
        mime, fmt = "font/ttf", "truetype"
    elif ext == ".otf":
        mime, fmt = "font/otf", "opentype"
    elif ext == ".woff":
        mime, fmt = "font/woff", "woff"
    elif ext == ".woff2":
        mime, fmt = "font/woff2", "woff2"
    else:
        mime, fmt = "font/otf", "opentype"

    return f"""
    @font-face {{
      font-family: "{family}";
      src: url("data:{mime};base64,{b64}") format("{fmt}");
      font-weight: 400;
      font-style: normal;
    }}
    """


# -----------------------------
# Size-fixed base CSS
# -----------------------------
def build_size_fixed_base_css(
    *,
    font_family: Optional[str] = None,
    font_size_px: int = 12,
    line_height: float = 1.25,
    cell_padding_px: int = 6,
    border_width_px: int = 1,
    border_style: str = "solid",
    text_color: str = "#111",
    page_bg: str = "#ffffff",
    table_bg: str = "#ffffff",
) -> str:
    # 폰트 지정이 있으면 그것을 우선, 없으면 기본 한글 폰트 사용
    if font_family:
        font_family_rule = f'''
        font-family: {font_family}, {DEFAULT_KOREAN_FONTS} !important;
        '''
    else:
        font_family_rule = f'''
        font-family: {DEFAULT_KOREAN_FONTS} !important;
        '''

    return f"""
    html, body {{
      margin: 0;
      padding: 0;
      background: {page_bg};
    }}

    /* 래퍼 */
    #shot {{
      display: inline-block;
      background: {table_bg};
    }}

    html, body, table, th, td, div, span, p, strong {{
      {font_family_rule}
      color: {text_color};
      font-size: {font_size_px}px;
      line-height: {line_height};
      font-weight: 400;
    }}

    #shot table {{
      border-collapse: collapse;
      table-layout: fixed;
      width: auto;
      background: {table_bg};
    }}

    #shot th, #shot td {{
      border: {border_width_px}px {border_style} #222;
      padding: {cell_padding_px}px;
      vertical-align: middle;
      word-break: break-word;
      overflow-wrap: anywhere;
    }}

    #shot th {{
      font-weight: 600;
      text-align: center;
    }}
    """


# -----------------------------
# Random themes
# -----------------------------
@dataclass(frozen=True)
class Theme:
    name: str
    border_color: str
    header_bg: str
    header_text: str
    stripe_bg: str
    body_bg: str
    shadow: str
    zebra: bool
    weight: float = 1.0


THEMES: List[Theme] = [
    Theme("gray_clean",  "#222222", "#f1f1f1", "#111111", "#fafafa", "#ffffff", "none", True, 3.5),
    Theme("soft_card",   "#d7dbe7", "#eef1f8", "#1f2430", "#f8f9fd", "#ffffff", "0 6px 18px rgba(0,0,0,0.08)", True, 1.0),
    Theme("blue_header", "#c8d3ea", "#2f5aa6", "#ffffff", "#f3f6ff", "#ffffff", "0 4px 14px rgba(47,90,166,0.12)", True, 0.2),
    Theme("mono",        "#333333", "#ffffff", "#111111", "#ffffff", "#ffffff", "none", False, 3.5),
]


def choose_weighted_theme(themes: List[Theme]) -> Theme:
    """가중치에 따라 테마를 선택합니다."""
    weights = [theme.weight for theme in themes]
    return random.choices(themes, weights=weights, k=1)[0]


def build_theme_css(theme: Theme) -> str:
    zebra_css = ""
    if theme.zebra:
        zebra_css = f"""
        #shot table tr:nth-child(even) td {{
          background: {theme.stripe_bg};
        }}
        """
    return f"""
    #shot th, #shot td {{
      border-color: {theme.border_color} !important;
      background: {theme.body_bg};
    }}

    #shot th {{
      background: {theme.header_bg} !important;
      color: {theme.header_text} !important;
    }}

    #shot table tr:first-child td {{
      background: {theme.header_bg};
      color: {theme.header_text};
      font-weight: 600;
      text-align: center;
    }}

    #shot {{
      box-shadow: {theme.shadow};
    }}

    {zebra_css}
    """


# -----------------------------
# Helpers
# -----------------------------
def wrap_table_fragment(table_html: str, font_family: Optional[str] = None) -> str:
    """
    HTML 조각을 완전한 문서로 래핑합니다.
    이미 완전한 HTML 문서인 경우에도 폰트 스타일을 추가합니다.
    """
    # 폰트 설정
    if font_family:
        font_css = f"font-family: {font_family}, {DEFAULT_KOREAN_FONTS};"
    else:
        font_css = f"font-family: {DEFAULT_KOREAN_FONTS};"
    
    # 폰트 강제 적용을 위한 스타일 태그
    font_override_style = f"""<style>
    * {{ {font_css} !important; }}
    body {{ {font_css} }}
    table, th, td {{ {font_css} }}
  </style>"""
    
    # 이미 완전한 HTML 문서인 경우 폰트 스타일만 삽입
    stripped = table_html.strip().lower()
    if stripped.startswith('<!doctype') or stripped.startswith('<html'):
        # </head> 앞에 스타일 삽입
        if '</head>' in table_html.lower():
            insert_pos = table_html.lower().find('</head>')
            return table_html[:insert_pos] + font_override_style + table_html[insert_pos:]
        elif '<body' in table_html.lower():
            # <head>가 없으면 <body> 앞에 삽입
            insert_pos = table_html.lower().find('<body')
            return table_html[:insert_pos] + f"<head>{font_override_style}</head>" + table_html[insert_pos:]
        else:
            return table_html  # 구조가 이상하면 그대로 반환
    
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>table</title>
  {font_override_style}
</head>
<body>
{table_html}
</body>
</html>"""


MEASURE_JS = r"""
() => {
  const cells = Array.from(document.querySelectorAll('#shot td, #shot th'));
  return cells.map(el => {
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100 };
  });
}
"""


def within_5pct(base: List[Dict[str, float]], cur: List[Dict[str, float]], tol: float = 0.05) -> bool:
    if len(base) != len(cur):
        return False
    lo, hi = 1.0 - tol, 1.0 + tol
    for b, c in zip(base, cur):
        bw = max(0.01, float(b["w"]))
        bh = max(0.01, float(b["h"]))
        rw = float(c["w"]) / bw
        rh = float(c["h"]) / bh
        if not (lo <= rw <= hi and lo <= rh <= hi):
            return False
    return True


# -----------------------------
# Main renderer (Updated for Dual Output)
# -----------------------------
async def render_table_dual_images(
    table_html: str,
    out_path_std: str,       # 기본 이미지 경로
    out_path_colored: str,   # 배경색 추가 이미지 경로
    *,
    font_path: Optional[str] = None,
    seed: Optional[int] = None,
    scale: float = 2.0,
    mt: int = 0, mr: int = 0, mb: int = 0, ml: int = 0,
    tol: float = 0.05,
    max_tries: int = 20,
    color_probability: float = 1.0,  # 색칠 확률 (0.0~1.0)
) -> Tuple[str, str, List[int]]:
    
    if seed is not None:
        random.seed(seed)

    # 경로 절대경로화
    out_path_std = str(Path(out_path_std).resolve())
    out_path_colored = str(Path(out_path_colored).resolve())

    # HTML에서 폰트 추출 (입력 HTML의 폰트 우선 사용)
    extracted_font = extract_font_family_from_html(table_html)
    
    html_doc = wrap_table_fragment(table_html, font_family=extracted_font)
    
    font_css = ""
    target_font_family = extracted_font  # HTML에서 추출한 폰트 사용
    if font_path:
        # 외부 폰트 파일이 지정된 경우 그것을 우선 사용
        target_font_family = "MyKR"
        font_css = font_face_base64(font_path, family=target_font_family)

    base_css = build_size_fixed_base_css(
        font_family=target_font_family,
        font_size_px=12,
        line_height=1.25,
        cell_padding_px=6,
        border_width_px=1,
        border_style="solid",
        page_bg="#ffffff",
        table_bg="#ffffff",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            device_scale_factor=scale,
            viewport={"width": 2200, "height": 2800},
            locale="ko-KR",  # 한국어 로케일 설정
        )

        await page.set_content(html_doc, wait_until="domcontentloaded")
        
        # 폰트 렌더링 대기
        await page.wait_for_timeout(100)

        if font_css:
            await page.add_style_tag(content=font_css)
            await page.evaluate("document.fonts && document.fonts.ready")
            
        await page.add_style_tag(content=base_css)

        # 래퍼(#shot) 생성 및 패딩 적용
        await page.evaluate(
            """({mt, mr, mb, ml}) => {
                const table = document.querySelector('table');
                if (!table) throw new Error('No <table> found');

                let shot = document.getElementById('shot');
                if (!shot) {
                    shot = document.createElement('div');
                    shot.id = 'shot';
                    document.body.prepend(shot);
                }
                shot.style.paddingTop = mt + 'px';
                shot.style.paddingRight = mr + 'px';
                shot.style.paddingBottom = mb + 'px';
                shot.style.paddingLeft = ml + 'px';
                shot.appendChild(table);
            }""",
            {"mt": mt, "mr": mr, "mb": mb, "ml": ml},
        )
        await page.wait_for_timeout(30)

        # Base metrics 측정
        base_metrics = await page.evaluate(MEASURE_JS)

        # 1. 안전한 테마 찾기 (색칠 확률 고려)
        should_apply_color = random.random() < color_probability
        chosen = None
        
        if should_apply_color:
            for _ in range(max_tries):
                theme = choose_weighted_theme(THEMES)
                await page.add_style_tag(content=build_theme_css(theme))
                await page.wait_for_timeout(30)
                cur_metrics = await page.evaluate(MEASURE_JS)

                if within_5pct(base_metrics, cur_metrics, tol=tol):
                    chosen = theme
                    break
        else:
            # 색칠하지 않을 경우 기본 테마 사용
            chosen = Theme("plain", "#222222", "#ffffff", "#111111", "#ffffff", "#ffffff", "none", False, 1.0)
            await page.add_style_tag(content=build_theme_css(chosen))

        if chosen is None:
            await browser.close()
            raise RuntimeError(f"Could not find a theme within tolerance.")

        applied_font = await page.evaluate(
            """() => getComputedStyle(document.querySelector('#shot') || document.body).fontFamily"""
        )
        shot = await page.query_selector("#shot")
        
        # 2. 기본 이미지 저장
        await shot.screenshot(path=out_path_std, omit_background=False)

        # 3. 유색 배경 이미지 생성 및 저장 (외부 배경만 변경 + 새로운 마진)
        bg_color = get_random_pastel_color()
        
        # 배경색 이미지용 새로운 랜덤 마진 적용
        new_margins = [random.randint(0, 5) for _ in range(4)]
        new_mt, new_mr, new_mb, new_ml = new_margins
        
        await page.evaluate(f"""({{color, mt, mr, mb, ml}}) => {{
            const shot = document.getElementById('shot');
            // 래퍼의 배경색 변경 (표 내부는 원래 테마 유지)
            shot.style.backgroundColor = color;
            // 새로운 마진 적용
            shot.style.paddingTop = mt + 'px';
            shot.style.paddingRight = mr + 'px';
            shot.style.paddingBottom = mb + 'px';
            shot.style.paddingLeft = ml + 'px';
        }}""", {"color": bg_color, "mt": new_mt, "mr": new_mr, "mb": new_mb, "ml": new_ml})
        
        await page.wait_for_timeout(30) # 렌더링 안정화
        await shot.screenshot(path=out_path_colored, omit_background=False)
        
        await browser.close()

    return chosen.name, applied_font, new_margins


# -----------------------------
# Batch Processor
# -----------------------------
def process_all_html_files(
    input_dir: str,
    output_dir: str,
    *,
    font_path: Optional[str] = None,
    scale: float = 2.0,
    overwrite: bool = False,
    generate_colored: bool = True,
    images_per_file: int = 1,
    color_probability: float = 1.0,
    raw_mode: bool = False,
):
    inp = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 모든 html 파일 검색
    html_files = list(inp.glob("*.html"))
    print("Found", len(html_files), "HTML files in", inp)
    if not html_files:
        print(f"No HTML files found in {inp}")
        return

    print(f"Found {len(html_files)} files. Starting conversion...")

    for i, html_file in enumerate(html_files):
        table_html = html_file.read_text(encoding="utf-8")
        # 마크다운 코드블록 제거
        table_html = clean_markdown_codeblocks(table_html)
        # <caption> 태그 제거
        table_html = remove_caption_tags(table_html)
        
        print(f"[{i+1}/{len(html_files)}] Processing {html_file.name}...")

        # 각 HTML 파일당 여러 이미지 생성
        for img_idx in range(images_per_file):
            # Raw 모드: 변환 없이 그대로 저장
            if raw_mode:
                stem = html_file.stem
                if images_per_file > 1:
                    raw_out = out / f"{stem}_v{img_idx + 1}.png"
                else:
                    raw_out = out / f"{stem}.png"
                
                if not overwrite:
                    counter = 1
                    while raw_out.exists():
                        if images_per_file > 1:
                            raw_out = out / f"{stem}_v{img_idx + 1}_{counter}.png"
                        else:
                            raw_out = out / f"{stem}_{counter}.png"
                        counter += 1
                
                try:
                    asyncio.run(
                        render_raw_html_image(
                            table_html,
                            str(raw_out),
                            scale=scale,
                        )
                    )
                    print(f"  -> v{img_idx + 1} Done (raw mode). Saved: {raw_out.name}")
                except Exception as e:
                    print(f"  -> v{img_idx + 1} Failed: {e}")
                continue

            # 랜덤 마진 설정 (1~5)
            margins = [random.randint(1, 5) for _ in range(4)]
            mt, mr, mb, ml = margins

            # 파일명 기반 출력 경로 설정
            stem = html_file.stem
            if images_per_file > 1:
                std_out = out / f"{stem}_v{img_idx + 1}.png"
                clr_out = out / f"{stem}_v{img_idx + 1}_colored.png"
            else:
                std_out = out / f"{stem}.png"
                clr_out = out / f"{stem}_colored.png"

            # 파일 덮어쓰기 확인
            if not overwrite:
                counter = 1
                original_std = std_out
                original_clr = clr_out
                while std_out.exists() or (generate_colored and clr_out.exists()):
                    if images_per_file > 1:
                        std_out = out / f"{stem}_v{img_idx + 1}_{counter}.png"
                        clr_out = out / f"{stem}_v{img_idx + 1}_{counter}_colored.png"
                    else:
                        std_out = out / f"{stem}_{counter}.png"
                        clr_out = out / f"{stem}_{counter}_colored.png"
                    counter += 1

            try:
                if generate_colored:
                    theme_name, _, new_margins = asyncio.run(
                        render_table_dual_images(
                            table_html,
                            str(std_out),
                            str(clr_out),
                            font_path=font_path,
                            scale=scale,
                            mt=mt, mr=mr, mb=mb, ml=ml,
                            tol=0.05,
                            max_tries=30,
                            color_probability=color_probability
                        )
                    )
                    print(f"  -> v{img_idx + 1} Done. Theme: {theme_name}, Margins: {margins} → Colored: {new_margins}")
                    print(f"  -> Saved: {std_out.name}, {clr_out.name}")
                else:
                    # 기본 이미지만 생성
                    theme_name, _ = asyncio.run(
                        render_table_single_image(
                            table_html,
                            str(std_out),
                            font_path=font_path,
                            scale=scale,
                            mt=mt, mr=mr, mb=mb, ml=ml,
                            tol=0.05,
                            max_tries=30,
                            color_probability=color_probability
                        )
                    )
                    print(f"  -> v{img_idx + 1} Done. Theme: {theme_name}, Margins: {margins}")
                    print(f"  -> Saved: {std_out.name}")
                
            except Exception as e:
                print(f"  -> v{img_idx + 1} Failed: {e}")


# Raw 이미지 생성 (변환 없이 그대로)
async def render_raw_html_image(
    html_content: str,
    out_path: str,
    *,
    scale: float = 2.0,
) -> None:
    """HTML을 아무런 변환 없이 그대로 이미지로 렌더링합니다."""
    out_path = str(Path(out_path).resolve())
    
    # HTML에서 폰트 추출
    extracted_font = extract_font_family_from_html(html_content)
    
    # 폰트 CSS 생성
    if extracted_font:
        font_css = f"font-family: {extracted_font}, {DEFAULT_KOREAN_FONTS};"
    else:
        font_css = f"font-family: {DEFAULT_KOREAN_FONTS};"
    
    # 폰트 강제 적용을 위한 스타일 태그
    font_override_style = f"""<style>
    * {{ {font_css} !important; }}
    body {{ {font_css} }}
    table, th, td {{ {font_css} }}
  </style>"""
    
    # HTML이 완전한 문서가 아니면 기본 래퍼 추가
    if not html_content.strip().lower().startswith('<!doctype') and not html_content.strip().lower().startswith('<html'):
        html_content = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  {font_override_style}
</head>
<body>
{html_content}
</body>
</html>"""
    else:
        # 완전한 HTML 문서에도 폰트 스타일 삽입 (</head> 앞에)
        if '</head>' in html_content.lower():
            insert_pos = html_content.lower().find('</head>')
            html_content = html_content[:insert_pos] + font_override_style + html_content[insert_pos:]
        elif '<body' in html_content.lower():
            # <head>가 없으면 <body> 앞에 삽입
            insert_pos = html_content.lower().find('<body')
            html_content = html_content[:insert_pos] + f"<head>{font_override_style}</head>" + html_content[insert_pos:]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            device_scale_factor=scale,
            viewport={"width": 2200, "height": 2800},
            locale="ko-KR",  # 한국어 로케일 설정
        )

        await page.set_content(html_content, wait_until="domcontentloaded")
        await page.wait_for_timeout(100)

        # 테이블이 있으면 테이블만, 없으면 body 전체 캡처
        table = await page.query_selector('table')
        if table:
            await table.screenshot(path=out_path, omit_background=False)
        else:
            body = await page.query_selector('body')
            await body.screenshot(path=out_path, omit_background=False)
        
        await browser.close()


# 단일 이미지 생성용 함수 추가
async def render_table_single_image(
    table_html: str,
    out_path: str,
    *,
    font_path: Optional[str] = None,
    seed: Optional[int] = None,
    scale: float = 2.0,
    mt: int = 0, mr: int = 0, mb: int = 0, ml: int = 0,
    tol: float = 0.05,
    max_tries: int = 20,
    color_probability: float = 1.0,
) -> Tuple[str, str]:
    
    if seed is not None:
        random.seed(seed)

    out_path = str(Path(out_path).resolve())
    
    # HTML에서 폰트 추출 (입력 HTML의 폰트 우선 사용)
    extracted_font = extract_font_family_from_html(table_html)
    
    html_doc = wrap_table_fragment(table_html, font_family=extracted_font)
    
    font_css = ""
    target_font_family = extracted_font  # HTML에서 추출한 폰트 사용
    if font_path:
        # 외부 폰트 파일이 지정된 경우 그것을 우선 사용
        target_font_family = "MyKR"
        font_css = font_face_base64(font_path, family=target_font_family)

    base_css = build_size_fixed_base_css(
        font_family=target_font_family,
        font_size_px=12,
        line_height=1.25,
        cell_padding_px=6,
        border_width_px=1,
        border_style="solid",
        page_bg="#ffffff",
        table_bg="#ffffff",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            device_scale_factor=scale,
            viewport={"width": 2200, "height": 2800},
            locale="ko-KR",  # 한국어 로케일 설정
        )

        await page.set_content(html_doc, wait_until="domcontentloaded")
        
        # 폰트 렌더링 대기
        await page.wait_for_timeout(100)

        if font_css:
            await page.add_style_tag(content=font_css)
            await page.evaluate("document.fonts && document.fonts.ready")
            
        await page.add_style_tag(content=base_css)

        await page.evaluate(
            """({mt, mr, mb, ml}) => {
                const table = document.querySelector('table');
                if (!table) throw new Error('No <table> found');

                let shot = document.getElementById('shot');
                if (!shot) {
                    shot = document.createElement('div');
                    shot.id = 'shot';
                    document.body.prepend(shot);
                }
                shot.style.paddingTop = mt + 'px';
                shot.style.paddingRight = mr + 'px';
                shot.style.paddingBottom = mb + 'px';
                shot.style.paddingLeft = ml + 'px';
                shot.appendChild(table);
            }""",
            {"mt": mt, "mr": mr, "mb": mb, "ml": ml},
        )
        await page.wait_for_timeout(30)

        base_metrics = await page.evaluate(MEASURE_JS)

        should_apply_color = random.random() < color_probability
        chosen = None
        
        if should_apply_color:
            for _ in range(max_tries):
                theme = choose_weighted_theme(THEMES)
                await page.add_style_tag(content=build_theme_css(theme))
                await page.wait_for_timeout(30)
                cur_metrics = await page.evaluate(MEASURE_JS)

                if within_5pct(base_metrics, cur_metrics, tol=tol):
                    chosen = theme
                    break
        else:
            chosen = Theme("plain", "#222222", "#ffffff", "#111111", "#ffffff", "#ffffff", "none", False, 1.0)
            await page.add_style_tag(content=build_theme_css(chosen))

        if chosen is None:
            await browser.close()
            raise RuntimeError(f"Could not find a theme within tolerance.")

        applied_font = await page.evaluate(
            """() => getComputedStyle(document.querySelector('#shot') || document.body).fontFamily"""
        )
        shot = await page.query_selector("#shot")
        
        await shot.screenshot(path=out_path, omit_background=False)
        await browser.close()

    return chosen.name, applied_font


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert HTML tables to images with augmentation")
    parser.add_argument("--input-dir", default="GeneratedHTMLs", help="Input directory containing HTML files")
    parser.add_argument("--output-dir", default="Output_Images", help="Output directory for images")
    parser.add_argument("--font-path", default=None, help="Path to font file (TTF, OTF, WOFF, WOFF2)")
    parser.add_argument("--scale", type=float, default=2.0, help="Image scale factor")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--no-colored", action="store_true", help="Skip colored background images")
    parser.add_argument("--count", type=int, default=1, help="Number of images per HTML file")
    parser.add_argument("--color-probability", type=float, default=0.7, help="Probability of applying colors to tables (0.0-1.0)")
    parser.add_argument("--theme-weights", nargs=4, type=float, default=[3.0, 2.5, 0.3, 1.5], 
                       help="Weights for themes: gray_clean soft_card blue_header mono")
    parser.add_argument("--raw", action="store_true", 
                       help="Convert HTML to image without any transformation (no themes, fonts, margins)")
    
    args = parser.parse_args()
    
    # 테마 가중치 업데이트
    if len(args.theme_weights) == 4:
        for i, weight in enumerate(args.theme_weights):
            THEMES[i] = replace(THEMES[i], weight=weight)
    
    # 설정 출력
    print("=" * 50)
    print("HTML to Image Converter (with Augmentation)")
    print("=" * 50)
    print(f"Input:  {args.input_dir}")
    print(f"Output: {args.output_dir}")
    print(f"Raw mode: {args.raw}")
    if not args.raw:
        print(f"Font: {args.font_path or 'System default'}")
        print(f"Generate colored: {not args.no_colored}")
        print(f"Color probability: {args.color_probability:.1%}")
        print(f"Theme weights: {[f'{t.name}={t.weight}' for t in THEMES]}")
    print(f"Scale: {args.scale}x")
    print(f"Overwrite: {args.overwrite}")
    print(f"Images per file: {args.count}")
    print("-" * 50)
    
    process_all_html_files(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        font_path=args.font_path,
        scale=args.scale,
        overwrite=args.overwrite,
        generate_colored=not args.no_colored,
        images_per_file=args.count,
        color_probability=args.color_probability,
        raw_mode=args.raw,
    )