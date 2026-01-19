"""
HTML을 이미지로 변환하는 스크립트
- 이미지가 너무 길 경우 행(row) 단위로 분할하여 저장
- 셀이 중간에 잘리지 않도록 처리
"""

import asyncio
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

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
    """
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


@dataclass
class RowInfo:
    """테이블 행 정보"""
    index: int
    top: float
    bottom: float
    height: float


def clean_markdown_codeblocks(content: str) -> str:
    """HTML 내용에서 마크다운 코드블록(```html ... ```)을 제거합니다."""
    content = content.strip()
    
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]
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


def wrap_html_document(html_content: str, font_family: Optional[str] = None) -> str:
    """HTML 조각을 완전한 문서로 래핑합니다. 완전한 HTML 문서에도 폰트 스타일을 추가합니다."""
    
    # 폰트 설정: 추출된 폰트가 있으면 사용, 없으면 기본 한글 폰트
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
    stripped = html_content.strip().lower()
    if stripped.startswith('<!doctype') or stripped.startswith('<html'):
        # </head> 앞에 스타일 삽입
        if '</head>' in html_content.lower():
            insert_pos = html_content.lower().find('</head>')
            return html_content[:insert_pos] + font_override_style + html_content[insert_pos:]
        elif '<body' in html_content.lower():
            # <head>가 없으면 <body> 앞에 삽입
            insert_pos = html_content.lower().find('<body')
            return html_content[:insert_pos] + f"<head>{font_override_style}</head>" + html_content[insert_pos:]
        else:
            return html_content  # 구조가 이상하면 그대로 반환
    
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Table</title>
  <style>
    body {{
      margin: 0;
      padding: 10px;
      background: white;
      {font_css}
    }}
    table {{
      border-collapse: collapse;
      {font_css}
      font-size: 12px;
    }}
    th, td {{
      border: 1px solid #333;
      padding: 6px 8px;
      vertical-align: middle;
    }}
    th {{
      background: #f5f5f5;
      font-weight: 600;
      text-align: center;
    }}
  </style>
  {font_override_style}
</head>
<body>
{html_content}
</body>
</html>"""


async def get_table_row_positions(page) -> Tuple[List[RowInfo], float, float]:
    """
    테이블의 각 행(tr)의 위치 정보를 가져옵니다.
    Returns: (행 정보 리스트, 테이블 전체 높이, 테이블 너비)
    """
    result = await page.evaluate("""
    () => {
        const table = document.querySelector('table');
        if (!table) return null;
        
        const tableRect = table.getBoundingClientRect();
        const rows = table.querySelectorAll('tr');
        const rowInfos = [];
        
        rows.forEach((row, index) => {
            const rect = row.getBoundingClientRect();
            rowInfos.push({
                index: index,
                top: rect.top - tableRect.top,
                bottom: rect.bottom - tableRect.top,
                height: rect.height
            });
        });
        
        return {
            rows: rowInfos,
            tableHeight: tableRect.height,
            tableWidth: tableRect.width,
            tableTop: tableRect.top,
            tableLeft: tableRect.left
        };
    }
    """)
    
    if result is None:
        return [], 0, 0
    
    rows = [RowInfo(**r) for r in result['rows']]
    return rows, result['tableHeight'], result['tableWidth']


def calculate_split_points(rows: List[RowInfo], max_height: float) -> List[Tuple[int, int]]:
    """
    행을 기준으로 분할 지점을 계산합니다.
    Returns: [(시작 행 인덱스, 끝 행 인덱스), ...] 리스트
    """
    if not rows:
        return []
    
    splits = []
    start_idx = 0
    current_height = 0
    
    for i, row in enumerate(rows):
        # 현재 행을 추가했을 때 최대 높이를 초과하는지 확인
        if current_height + row.height > max_height and i > start_idx:
            # 이전 행까지를 하나의 분할로 저장
            splits.append((start_idx, i - 1))
            start_idx = i
            current_height = row.height
        else:
            current_height += row.height
    
    # 마지막 분할 추가
    if start_idx < len(rows):
        splits.append((start_idx, len(rows) - 1))
    
    return splits


async def render_html_with_split(
    html_content: str,
    output_path: str,
    *,
    max_height: int = 2000,
    scale: float = 2.0,
    padding: int = 10,
) -> List[str]:
    """
    HTML을 이미지로 렌더링하고, 필요시 행 단위로 분할합니다.
    
    Args:
        html_content: HTML 내용
        output_path: 출력 파일 경로 (분할 시 _1, _2 등이 추가됨)
        max_height: 이미지 최대 높이 (픽셀)
        scale: 이미지 스케일
        padding: 여백
    
    Returns:
        생성된 이미지 파일 경로 리스트
    """
    output_path = Path(output_path).resolve()
    output_dir = output_path.parent
    output_stem = output_path.stem
    output_ext = output_path.suffix or '.png'
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # HTML에서 폰트 추출
    extracted_font = extract_font_family_from_html(html_content)
    html_doc = wrap_html_document(html_content, font_family=extracted_font)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            device_scale_factor=scale,
            viewport={"width": 2200, "height": 4000},
            locale="ko-KR",
        )
        
        await page.set_content(html_doc, wait_until="domcontentloaded")
        await page.wait_for_timeout(100)
        
        # 테이블 행 위치 정보 가져오기
        rows, table_height, table_width = await get_table_row_positions(page)
        
        # 테이블이 없는 경우 전체 페이지 캡처
        if not rows:
            body = await page.query_selector('body')
            await body.screenshot(path=str(output_path), omit_background=False)
            await browser.close()
            return [str(output_path)]
        
        # 분할이 필요 없는 경우
        if table_height <= max_height:
            table = await page.query_selector('table')
            await table.screenshot(path=str(output_path), omit_background=False)
            await browser.close()
            return [str(output_path)]
        
        # 분할 지점 계산
        splits = calculate_split_points(rows, max_height)
        
        if len(splits) == 1:
            # 분할이 필요 없음
            table = await page.query_selector('table')
            await table.screenshot(path=str(output_path), omit_background=False)
            await browser.close()
            return [str(output_path)]
        
        # 각 분할 영역을 개별 이미지로 캡처
        output_files = []
        
        for part_idx, (start_row, end_row) in enumerate(splits, 1):
            # 분할된 파일명 생성
            part_path = output_dir / f"{output_stem}_{part_idx}{output_ext}"
            
            # 해당 행 범위의 클립 영역 계산
            start_top = rows[start_row].top
            end_bottom = rows[end_row].bottom
            
            # 테이블의 절대 위치 가져오기
            table_rect = await page.evaluate("""
            () => {
                const table = document.querySelector('table');
                const rect = table.getBoundingClientRect();
                return { top: rect.top, left: rect.left, width: rect.width };
            }
            """)
            
            clip = {
                'x': table_rect['left'] - padding,
                'y': table_rect['top'] + start_top - padding,
                'width': table_rect['width'] + padding * 2,
                'height': (end_bottom - start_top) + padding * 2,
            }
            
            await page.screenshot(
                path=str(part_path),
                clip=clip,
                omit_background=False
            )
            
            output_files.append(str(part_path))
            print(f"  Part {part_idx}: rows {start_row+1}-{end_row+1}, height={end_bottom - start_top:.0f}px")
        
        await browser.close()
    
    return output_files


def process_html_files(
    input_dir: str,
    output_dir: str,
    *,
    max_height: int = 2000,
    scale: float = 2.0,
    overwrite: bool = False,
):
    """
    디렉토리 내 모든 HTML 파일을 처리합니다.
    """
    inp = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    html_files = list(inp.glob("*.html"))
    
    if not html_files:
        print(f"No HTML files found in {inp}")
        return
    
    print(f"Found {len(html_files)} HTML files. Max height: {max_height}px")
    print("-" * 50)
    
    total_images = 0
    
    for i, html_file in enumerate(html_files):
        print(f"[{i+1}/{len(html_files)}] Processing {html_file.name}...")
        
        try:
            html_content = html_file.read_text(encoding="utf-8")
            html_content = clean_markdown_codeblocks(html_content)
            html_content = remove_caption_tags(html_content)
            
            output_path = out / f"{html_file.stem}.png"
            
            # 기존 파일 확인
            if not overwrite and output_path.exists():
                counter = 1
                while output_path.exists():
                    output_path = out / f"{html_file.stem}_{counter}.png"
                    counter += 1
            
            # 렌더링 및 분할
            output_files = asyncio.run(
                render_html_with_split(
                    html_content,
                    str(output_path),
                    max_height=max_height,
                    scale=scale,
                )
            )
            
            total_images += len(output_files)
            
            if len(output_files) == 1:
                print(f"  -> Saved: {Path(output_files[0]).name}")
            else:
                print(f"  -> Split into {len(output_files)} images")
            
        except Exception as e:
            print(f"  -> Failed: {e}")
    
    print("-" * 50)
    print(f"Done. Generated {total_images} images from {len(html_files)} HTML files.")


async def render_single_html(
    html_path: str,
    output_path: str,
    *,
    max_height: int = 2000,
    scale: float = 2.0,
):
    """단일 HTML 파일을 처리합니다."""
    html_content = Path(html_path).read_text(encoding="utf-8")
    html_content = clean_markdown_codeblocks(html_content)
    html_content = remove_caption_tags(html_content)
    
    output_files = await render_html_with_split(
        html_content,
        output_path,
        max_height=max_height,
        scale=scale,
    )
    
    return output_files


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert HTML tables to images with automatic splitting"
    )
    parser.add_argument(
        "--input-dir", 
        default="Output_QA", 
        help="Input directory containing HTML files"
    )
    parser.add_argument(
        "--output-dir", 
        default="Output_Images", 
        help="Output directory for images"
    )
    parser.add_argument(
        "--input-file",
        help="Process a single HTML file instead of directory"
    )
    parser.add_argument(
        "--output-file",
        help="Output file path (when using --input-file)"
    )
    parser.add_argument(
        "--max-height", 
        type=int, 
        default=2000, 
        help="Maximum image height before splitting (pixels)"
    )
    parser.add_argument(
        "--scale", 
        type=float, 
        default=2.0, 
        help="Image scale factor"
    )
    parser.add_argument(
        "--overwrite", 
        action="store_true", 
        help="Overwrite existing files"
    )
    
    args = parser.parse_args()
    
    print(f"HTML to Image Converter (with auto-split)")
    print(f"Max height: {args.max_height}px")
    print(f"Scale: {args.scale}x")
    print("-" * 50)
    
    if args.input_file:
        # 단일 파일 처리
        output_path = args.output_file or f"{Path(args.input_file).stem}.png"
        output_files = asyncio.run(
            render_single_html(
                args.input_file,
                output_path,
                max_height=args.max_height,
                scale=args.scale,
            )
        )
        print(f"Generated {len(output_files)} image(s):")
        for f in output_files:
            print(f"  - {f}")
    else:
        # 디렉토리 처리
        process_html_files(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            max_height=args.max_height,
            scale=args.scale,
            overwrite=args.overwrite,
        )
