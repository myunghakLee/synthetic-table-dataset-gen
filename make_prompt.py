import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# -----------------------------
# Constants (data only)
# -----------------------------
INTROS: List[str] = [
    "HTML 코드를 사용하여 표를 하나 작성해.",
    "웹페이지에 들어갈 HTML Table 하나만 만들어줘.",
    "데이터 파싱 테스트를 위한 HTML 표를 생성해라.",
    "보고서에 첨부할 깔끔한 HTML 표 코드를 줘.",
]

BASE_CONSTRAINTS: List[str] = [
    "개인정보(이름, 전화번호)는 실제와 유사한 한국인 가상 데이터를 사용하며 그 외 주소및 숫자등 역시 실제 데이터처럼 보여야 한다.",
    "반드시 하나의 표로 구성되어야 한다.",
    "Table Margin은 따로 설정하지 말아라.",
]

DATA_CONSTRAINTS: List[str] = [
    "날짜 데이터는 'YYYY.MM.DD' 형식을 반드시 지켜라.",  #  10
    "모든 금액 데이터에는 천 단위 콤마(,)를 붙여라.",     # 5
    "일부 셀에는 'N/A' 또는 공란을 포함시켜라.",         # 15
    "다량의 텍스트가 셀안에 포함된 표를 만들어라.",       # 5
    "일부 셀에 공란을 포함시켜라.",                     # 15
    "데이터에 한글과 영어를 7:3 비율로 섞어서 작성해라.",  # 15
    "한자를 일부 사용하라(예: 김현우(金賢佑))."          # 5
    "한글이 메인이되 한자와 영어가 일부 섞이도록 해라.",   # 5
    "비어있는 셀(공란)을 많이 만들어라.",   # 10
    "맨 왼쪽 위는 비어있는 셀로 만들어라.",   # 15
]

DATA_CONSTRAINTS_WEIGHTS: List[int] = [10, 5, 15, 5, 15, 15, 5, 5, 10, 15]

MERGE_STYLES: List[str] = [
    "헤더(Header) 부분에 복잡한 셀 병합을 적용해라.",
    "좌측 첫 번째 열(분류 열)을 세로로 병합해라.",
    "불규칙하게 셀을 병합하여 구조를 복잡하게 만들어라.",
]

BORDER_STYLES: List[str] = ["실선(solid)", "이중선(double)", "점선(dotted)", "테두리 없음(border:0)"]
BORDER_WEIGHTS: List[int] = [70, 5, 5, 20]

FONTS: List[str] = ["궁서체 계열", "고딕체 계열", "타자기체"]
HEADER_BG_CHOICES: List[str] = ["파스텔톤", "원색에 가까운 진한 색", "회색조 배경"]

DOMAIN_SETTINGS: Dict[str, Dict[str, object]] = {
    "공공기관": {"weight": 40, "forms": ["주민등록등본", "지출결의서", "회의록", "근로계약서", "사업자등록증"]},
    "의료/병원": {"weight": 35, "forms": ["환자 진료 기록", "혈액 검사 결과지", "입퇴원 확인서", "처방전"]},
    "금융/회계": {"weight": 10, "forms": ["주민등록등본", "월간 손익계산서", "카드 사용 내역", "환율 변동표", "대출 상환표"]},
    "물류/재고": {"weight": 10, "forms": ["창고 재고 목록", "일일 배송 리스트", "식자재 발주서", "차량 운행 일지"]},
    "IT/개발": {"weight": 5, "forms": ["서버 에러 로그", "API 응답 명세서", "DB 스키마", "IP 접속 기록"]},
}


# -----------------------------
# Configuration dataclasses
# -----------------------------
@dataclass
class StructureConfig:
    """표 구조 관련 설정"""
    rows: int
    cols: int
    merge_styles: List[str] = field(default_factory=list)
    use_column_mismatch: bool = False


@dataclass
class StyleConfig:
    """스타일 관련 설정"""
    use_stripe: bool = False
    border_styles: List[str] = field(default_factory=list)
    color_mode: str = "default"  # "grayscale", "header_bg", "default"
    header_bg: str = ""
    font: str = ""


# -----------------------------
# Helpers (logic only)
# -----------------------------
def weighted_choice(options: List[str], weights: List[int]) -> str:
    """Return one option based on weights."""
    return random.choices(options, weights=weights, k=1)[0]


def select_domain_and_form(domain_settings: Dict[str, Dict[str, object]]) -> Tuple[str, str]:
    """Pick a domain by weight, then pick one form inside that domain."""
    domains = list(domain_settings.keys())
    weights = [int(domain_settings[d]["weight"]) for d in domains]
    domain = weighted_choice(domains, weights)
    form = random.choice(list(domain_settings[domain]["forms"]))  # type: ignore[arg-type]
    return domain, form


# -----------------------------
# Config generators (랜덤 결정 로직)
# -----------------------------
def generate_data_constraints(count: int) -> List[str]:
    """지정된 개수만큼 데이터 제약조건을 샘플링하여 반환"""
    if count <= 0:
        return []
    return random.sample(DATA_CONSTRAINTS, k=min(count, len(DATA_CONSTRAINTS)))


def generate_structure_config() -> StructureConfig:
    """표 구조 설정을 생성하여 반환"""
    rows = random.randint(3, 16)
    cols = random.randint(2, 10)
    
    merge_styles: List[str] = []
    use_column_mismatch = False
    
    # 80% 확률로 병합 스타일 추가
    if random.random() < 0.8:
        pool = MERGE_STYLES[:]
        random.shuffle(pool)
        merge_styles.append(pool.pop())  # 최소 1개
        while pool and random.random() < 0.5:
            merge_styles.append(pool.pop())
        
        use_column_mismatch = random.random() < 0.3
    
    return StructureConfig(
        rows=rows,
        cols=cols,
        merge_styles=merge_styles,
        use_column_mismatch=use_column_mismatch,
    )


def generate_style_config() -> StyleConfig:
    """스타일 설정을 생성하여 반환"""
    config = StyleConfig(font=random.choice(FONTS))
    
    # 50% 확률로 스트라이프 + 테두리 스타일
    if random.random() < 0.5:
        config.use_stripe = True
        
        action = weighted_choice(["single", "double", "various"], [50, 25, 25])
        if action == "single":
            config.border_styles = [weighted_choice(BORDER_STYLES, BORDER_WEIGHTS)]
        elif action == "double":
            config.border_styles = [
                weighted_choice(BORDER_STYLES, BORDER_WEIGHTS),
                weighted_choice(BORDER_STYLES, BORDER_WEIGHTS),
            ]
        # "various"인 경우 border_styles는 빈 리스트 유지
    
    # 색상 모드 결정
    seed = random.random()
    if seed < 0.3:
        config.color_mode = "grayscale"
    elif seed < 0.35:
        config.color_mode = "header_bg"
        config.header_bg = random.choice(HEADER_BG_CHOICES)
    
    return config


# -----------------------------
# Prompt builders (설정을 텍스트로 변환)
# -----------------------------
def build_structure_prompt(config: StructureConfig) -> List[str]:
    """구조 설정을 프롬프트 문자열 리스트로 변환"""
    parts: List[str] = []
    # parts.append(f"표의 종횡비는 대략 {config.rows}:{config.cols}수준으로 만들어라.")
    parts.extend(config.merge_styles)
    
    if config.use_column_mismatch:
        parts.append(
            "단, HTML상으로는 표의 전체 너비는 맞지만 내부 셀들의 열 너비가 서로 맞지 않는 '열 불일치' 스타일로 만들어라."
        )
    return parts


def build_style_prompt(config: StyleConfig) -> str:
    """스타일 설정을 프롬프트 문자열로 변환"""
    req: List[str] = []
    
    if config.use_stripe:
        req.append("표에 음영(스트라이프) 효과를 넣어라.")
        
        if len(config.border_styles) == 1:
            req.append(f"테두리는 {config.border_styles[0]} 스타일을 사용해라.")
        elif len(config.border_styles) == 2:
            req.append(f"테두리는 {config.border_styles[0]} 및 {config.border_styles[1]} 스타일을 혼용해라.")
        elif config.use_stripe:  # various case
            req.append("테두리는 다양한 스타일을 사용해라.")
    
    if config.color_mode == "grayscale":
        req.append("표는 흑백(Grayscale)으로만 스타일링해라.")
    elif config.color_mode == "header_bg" and config.header_bg:
        req.append(f"헤더 배경색은 {config.header_bg}을 사용해라.")
    
    req.append(f"글꼴은 {config.font} 느낌을 줘라.")
    
    return ", ".join(req)


# -----------------------------
# Main
# -----------------------------
def generate_weighted_prompt() -> str:
    parts: List[str] = []

    # 1) Intro + base constraints
    parts.append(random.choice(INTROS))
    parts.extend(BASE_CONSTRAINTS)

    # 2) Domain (weighted) + specific form
    if random.random() < 0.7:
        domain, form = select_domain_and_form(DOMAIN_SETTINGS)
        parts.append(f"주제는 '{domain}' 분야의 '{form}' 양식이어야 한다.")

    # 3) Data constraints (0~2개 랜덤 결정)
    data_constraint_count = random.randint(0, 2)
    parts.extend(generate_data_constraints(data_constraint_count))

    # 4) Structure complexity (설정 생성 후 프롬프트로 변환)
    structure_config = generate_structure_config()
    parts.extend(build_structure_prompt(structure_config))

    # 5) Style (설정 생성 후 프롬프트로 변환)
    style_config = generate_style_config()
    parts.append(f"스타일 요구사항: {build_style_prompt(style_config)}")
    
    parts.append("답변은 오직 HTML 코드만 출력하고 설명은 생략해라.")

    return "\n".join(parts)


if __name__ == "__main__":
    for _ in range(10):
        print("\n--- 생성된 프롬프트 예시 ---")
        print(generate_weighted_prompt())
