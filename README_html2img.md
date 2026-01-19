# HTML2IMG - HTML 테이블을 이미지로 변환

HTML 테이블을 고품질 PNG 이미지로 변환하는 Python 도구입니다. 다양한 테마와 스타일링 옵션을 제공하여 시각적으로 매력적인 테이블 이미지를 생성할 수 있습니다.

## 주요 기능

### 🎨 다양한 테마

- **gray_clean**: 깔끔한 회색 테마 (기본 가중치: 3.0)
- **soft_card**: 부드러운 카드 스타일 (기본 가중치: 2.5)
- **blue_header**: 파란색 헤더 테마 (기본 가중치: 2.0)
- **mono**: 미니멀한 단색 테마 (기본 가중치: 1.5)

### 🎲 스마트한 랜덤화

- **가중치 기반 테마 선택**: 각 테마별로 다른 선택 확률
- **색칠 확률 제어**: 테이블에 색상을 적용할 확률 조정 가능
- **랜덤 마진**: 1-5픽셀 범위의 무작위 여백 적용

### 🖼️ 듀얼 이미지 생성

- **기본 이미지**: 테마가 적용된 기본 테이블 이미지
- **배경색 이미지**: 파스텔톤 배경색이 추가된 버전 (다른 마진 적용)

### ⚙️ 고급 옵션

- **폰트 지원**: 커스텀 폰트 파일 (TTF, OTF, WOFF, WOFF2) 지원
- **스케일 조정**: 이미지 해상도 조정 가능
- **배치 처리**: 여러 HTML 파일 일괄 변환

## 설치 요구사항

```bash
pip install playwright
playwright install chromium
```

## 사용법

### 기본 사용법

```bash
python html2img.py
```

기본적으로 `Output_QA` 폴더의 HTML 파일들을 `Output_Images` 폴더에 이미지로 변환합니다.

### 명령행 옵션

| 옵션                  | 기본값                 | 설명                         |
| --------------------- | ---------------------- | ---------------------------- |
| `--input-dir`         | `Output_QA`            | HTML 파일이 있는 입력 폴더   |
| `--output-dir`        | `Output_Images`        | 이미지를 저장할 출력 폴더    |
| `--font-path`         | `None`                 | 사용할 폰트 파일 경로        |
| `--scale`             | `2.0`                  | 이미지 스케일 배율           |
| `--overwrite`         | `False`                | 기존 파일 덮어쓰기           |
| `--no-colored`        | `False`                | 배경색 이미지 생성 생략      |
| `--count`             | `1`                    | HTML 파일당 생성할 이미지 수 |
| `--color-probability` | `1.0`                  | 색칠 확률 (0.0-1.0)          |
| `--theme-weights`     | `[3.0, 2.5, 2.0, 1.5]` | 테마 가중치                  |

### 사용 예시

#### 1. 기본 변환

```bash
python html2img.py --input-dir Output_simple --output-dir MyImages
```

#### 2. 색칠 확률 조정 (50% 확률로만 색칠)

```bash
python html2img.py --color-probability 0.5
```

#### 3. 테마 가중치 변경 (mono 테마를 더 자주 사용)

```bash
python html2img.py --theme-weights 1.0 1.0 1.0 5.0
```

#### 4. 고해상도 이미지 생성

```bash
python html2img.py --scale 3.0 --count 5
```

#### 5. 커스텀 폰트 사용

```bash
python html2img.py --font-path "fonts/NanumGothic.ttf" --scale 2.5
```

#### 6. 배경색 없는 이미지만 생성

```bash
python html2img.py --no-colored --color-probability 0.8
```

## 출력 파일 형식

### 파일명 패턴

- **기본 이미지**: `{원본파일명}.png`
- **배경색 이미지**: `{원본파일명}_colored.png`
- **여러 버전**: `{원본파일명}_v{번호}.png`, `{원본파일명}_v{번호}_colored.png`

### 파일 구조 예시

```
Output_Images/
├── table1.png
├── table1_colored.png
├── table2_v1.png
├── table2_v1_colored.png
├── table2_v2.png
└── table2_v2_colored.png
```

## 테마 상세

### Gray Clean (기본 가중치: 3.0)

- 깔끔한 회색 톤
- 짝수 행 스트라이프 효과
- 그림자 없음

### Soft Card (기본 가중치: 2.5)

- 부드러운 파스텔 블루 톤
- 카드 스타일 그림자 효과
- 우아한 외관

### Blue Header (기본 가중치: 2.0)

- 파란색 헤더 강조
- 전문적인 비즈니스 룩
- 중간 정도의 그림자

### Mono (기본 가중치: 1.5)

- 흑백 미니멀 디자인
- 스트라이프 효과 없음
- 깔끔한 단순함

## 고급 설정

### 색칠 확률 시스템

- `--color-probability 1.0`: 항상 색칠 (기본값)
- `--color-probability 0.7`: 70% 확률로 색칠
- `--color-probability 0.0`: 색칠 안함 (plain 테마 사용)

### 가중치 시스템

테마 선택 확률은 가중치에 비례합니다:

- `gray_clean` (3.0): 약 33% 확률
- `soft_card` (2.5): 약 28% 확률
- `blue_header` (2.0): 약 22% 확률
- `mono` (1.5): 약 17% 확률

### 마진 랜덤화

- 각 이미지마다 1-5픽셀 범위의 랜덤 마진 적용
- 기본 이미지와 배경색 이미지는 서로 다른 마진 사용
- 자연스러운 변화 효과 제공

## 문제 해결

### 일반적인 오류

1. **Playwright 설치 오류**: `playwright install chromium` 실행
2. **폰트 로딩 실패**: 폰트 파일 경로 확인
3. **메모리 부족**: `--scale` 값을 낮추거나 `--count` 줄이기

### 성능 최적화

- 대량 처리 시 `--scale` 값을 낮추세요 (예: 1.5)
- `--count` 값을 적게 설정하세요
- 불필요한 경우 `--no-colored` 옵션 사용

## 라이선스

이 프로젝트는 테이블 데이터 시각화를 위한 도구입니다.

---

**Tip**: 다양한 옵션을 조합하여 프로젝트 요구사항에 맞는 최적의 이미지를 생성하세요!
