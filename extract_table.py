"""
HTML 파일에서 <table>...</table>만 추출하고 모든 스타일과 줄바꿈을 제거하는 유틸리티
"""

import re
from bs4 import BeautifulSoup, NavigableString, Comment
from pathlib import Path
from typing import Optional


# 제거할 속성 목록
STYLE_ATTRIBUTES = [
    "style",
    "class",
    "id",
    "align",
    "valign",
    "width",
    "height",
    "bgcolor",
    "border",
    "cellpadding",
    "cellspacing",
]


def normalize_text(text: str) -> str:
    """
    텍스트 내부의 연속 공백/줄바꿈을 단일 공백으로 변환합니다.
    """
    # 모든 공백 문자(줄바꿈, 탭 포함)를 단일 공백으로
    return re.sub(r"\s+", " ", text).strip()


def remove_whitespace(html: str) -> str:
    """
    HTML 태그 사이의 불필요한 공백과 줄바꿈을 제거합니다.
    """
    # 태그 사이의 공백/줄바꿈 제거: >    < → ><
    html = re.sub(r">\s+<", "><", html)
    # 앞뒤 공백 제거
    html = html.strip()
    return html


def extract_clean_table(html_content: str) -> Optional[str]:
    """
    HTML 문자열에서 <table>을 추출하고 스타일 관련 속성과 줄바꿈을 모두 제거합니다.
    
    Args:
        html_content: 원본 HTML 문자열
        
    Returns:
        스타일과 줄바꿈이 제거된 <table> HTML 문자열, 테이블이 없으면 None
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 첫 번째 table 태그 찾기
    table = soup.find("table")
    if table is None:
        return None
    
    # table 내 모든 태그에서 스타일 속성 제거
    for tag in table.find_all(True):  # True = 모든 태그
        for attr in STYLE_ATTRIBUTES:
            if tag.has_attr(attr):
                del tag[attr]
    
    # table 자체의 스타일 속성도 제거
    for attr in STYLE_ATTRIBUTES:
        if table.has_attr(attr):
            del table[attr]
    
    # <style> 태그 제거 (table 내부에 있을 경우)
    for style_tag in table.find_all("style"):
        style_tag.decompose()
    
    # <br> 태그 제거
    for br_tag in table.find_all("br"):
        br_tag.decompose()
    
    # <thead>, <tbody>, <tfoot> 태그 제거 (내용은 유지)
    for wrapper_tag in table.find_all(["thead", "tbody", "tfoot"]):
        wrapper_tag.unwrap()
    
    # <caption> 태그 제거
    for caption_tag in table.find_all("caption"):
        caption_tag.decompose()
    
    # 스타일 관련 태그 제거 (내용은 유지): <strong>, <b>, <i>, <em>, <u>, <span>, <font>, <mark> 등
    style_tags = ["strong", "b", "i", "em", "u", "span", "font", "mark", "small", "big", "sub", "sup", "s", "strike", "del", "ins", "abbr", "cite", "code", "kbd", "samp", "var"]
    for tag_name in style_tags:
        for style_tag in table.find_all(tag_name):
            style_tag.unwrap()
    
    # HTML 주석 제거 (<!-- ... -->)
    for comment in table.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # 텍스트 노드 내부의 공백/줄바꿈 정규화
    for text_node in table.find_all(string=True):
        if isinstance(text_node, NavigableString):
            normalized = normalize_text(str(text_node))
            if normalized:
                text_node.replace_with(normalized)
            elif text_node.strip() == "":
                text_node.extract()  # 빈 텍스트 노드 제거
    
    # HTML 문자열로 변환 후 태그 간 줄바꿈/공백 제거
    result = str(table)
    result = remove_whitespace(result)
    
    return result


def extract_clean_table_from_file(file_path: str) -> Optional[str]:
    """
    파일에서 HTML을 읽어 clean table을 추출합니다.
    
    Args:
        file_path: HTML 파일 경로
        
    Returns:
        스타일이 제거된 <table> HTML 문자열
    """
    path = Path(file_path)
    html_content = path.read_text(encoding="utf-8")
    return extract_clean_table(html_content)


def process_html_file(input_path: str, output_path: Optional[str] = None) -> str:
    """
    HTML 파일을 처리하여 clean table을 추출하고 저장합니다.
    
    Args:
        input_path: 입력 HTML 파일 경로
        output_path: 출력 파일 경로 (None이면 _clean 접미사 붙임)
        
    Returns:
        저장된 파일 경로
    """
    clean_table = extract_clean_table_from_file(input_path)
    
    if clean_table is None:
        raise ValueError(f"No table found in {input_path}")
    
    if output_path is None:
        input_p = Path(input_path)
        output_path = str(input_p.parent / f"{input_p.stem}_clean{input_p.suffix}")
    
    Path(output_path).write_text(clean_table, encoding="utf-8")
    return output_path


# 일괄 처리용 함수 (main_batch.py에서 사용)
def clean_html_response(html_content: str) -> str:
    """
    Gemini 응답에서 받은 HTML을 정제합니다.
    - 마크다운 코드블록 제거 (```html ... ```)
    - <table>만 추출
    - 모든 스타일 제거
    
    Args:
        html_content: Gemini API 응답 텍스트
        
    Returns:
        정제된 table HTML
    """
    content = html_content.strip()
    
    # 마크다운 코드블록 제거
    if content.startswith("```"):
        lines = content.split("\n")
        # 첫 줄 (```html 등) 제거
        lines = lines[1:]
        # 마지막 줄 (```) 제거
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    
    # table 추출 및 스타일 제거
    clean_table = extract_clean_table(content)
    
    return clean_table if clean_table else content


def process_output_qa_folder(input_folder: str = "Output_QA", output_folder: str = "Output_simple") -> int:
    """
    Output_QA 폴더의 모든 HTML 파일을 처리하여 정제된 테이블을 Output_simple 폴더에 저장합니다.
    
    Args:
        input_folder: 입력 폴더 경로 (기본: Output_QA)
        output_folder: 출력 폴더 경로 (기본: Output_simple)
        
    Returns:
        처리된 파일 개수
    """
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    if not input_path.exists():
        print(f"[!] Input folder '{input_folder}' does not exist.")
        return 0
    
    # 출력 폴더 생성
    output_path.mkdir(parents=True, exist_ok=True)
    
    # HTML 파일들 찾기
    html_files = list(input_path.glob("*.html"))
    if not html_files:
        print(f"[!] No HTML files found in '{input_folder}'")
        return 0
    
    print(f"[*] Found {len(html_files)} HTML files in '{input_folder}'")
    
    success_count = 0
    failed_files = []
    
    for html_file in html_files:
        try:
            # HTML 파일 읽기
            html_content = html_file.read_text(encoding="utf-8")
            
            # 정제된 테이블 추출
            clean_table = clean_html_response(html_content)
            
            if clean_table and clean_table.strip():
                # 출력 파일 경로
                output_file = output_path / html_file.name
                
                # 파일 저장
                output_file.write_text(clean_table, encoding="utf-8")
                success_count += 1
                print(f"    [✓] {html_file.name} → {output_file.name}")
            else:
                failed_files.append(html_file.name)
                print(f"    [!] No valid table found in {html_file.name}")
                
        except Exception as e:
            failed_files.append(html_file.name)
            print(f"    [!] Error processing {html_file.name}: {e}")
    
    print(f"\n[*] Processing completed: {success_count} successful, {len(failed_files)} failed")
    if failed_files:
        print(f"[*] Failed files: {', '.join(failed_files[:5])}" + ("..." if len(failed_files) > 5 else ""))
    
    return success_count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract and clean HTML tables (remove styles, keep structure only)"
    )
    parser.add_argument(
        "--input-dir",
        default="GeneratedHTMLs",
        help="Input directory containing HTML files"
    )
    parser.add_argument(
        "--output-dir",
        default="Output_Labels",
        help="Output directory for cleaned HTML labels"
    )
    parser.add_argument(
        "--input-file",
        help="Process a single HTML file instead of directory"
    )
    parser.add_argument(
        "--output-file",
        help="Output file path (when using --input-file)"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("HTML Table Extractor (Label Generator)")
    print("=" * 50)
    
    if args.input_file:
        # 단일 파일 처리
        try:
            output = process_html_file(args.input_file, args.output_file)
            print(f"[✓] Saved to: {output}")
        except Exception as e:
            print(f"[!] Error: {e}")
    else:
        # 디렉토리 일괄 처리
        print(f"Input:  {args.input_dir}")
        print(f"Output: {args.output_dir}")
        print("-" * 50)
        
        count = process_output_qa_folder(args.input_dir, args.output_dir)
        print("-" * 50)
        print(f"[✓] {count} files processed successfully!")
