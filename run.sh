#!/bin/bash
#
# Table Parsing 모델 파인튜닝을 위한 Synthetic Data 생성 파이프라인
#
# 워크플로우:
#   1. Gemini API로 HTML 테이블 생성 (main_batch.py)
#   2. HTML → 이미지 변환 + Augmentation (html2img.py)
#   3. HTML 정제 → Label 생성 (extract_table.py)
#

set -e  # 에러 발생 시 중단

# ============================================
# 기본값 설정
# ============================================
NUM_PROMPTS=100
IMAGES_PER_FILE=1
COLOR_PROBABILITY=0.1
SCALE=2.0
OUTPUT_HTML="GeneratedHTMLs"
OUTPUT_IMAGES="Output_Images"
OUTPUT_LABELS="Output_Labels"

SKIP_GENERATE=false
SKIP_IMAGES=false
SKIP_LABELS=false

# ============================================
# 도움말 함수
# ============================================
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Table Parsing 모델 파인튜닝을 위한 Synthetic Data 생성 파이프라인

OPTIONS:
  --num-prompts N        생성할 HTML 테이블 수 (기본: $NUM_PROMPTS)
  --images-per-file N    HTML당 생성할 이미지 수 (기본: $IMAGES_PER_FILE)
  --color-probability P  색상 테마 적용 확률 0.0~1.0 (기본: $COLOR_PROBABILITY)
  --scale N              이미지 스케일 배율 (기본: $SCALE)
  --output-html DIR      생성된 HTML 저장 폴더 (기본: $OUTPUT_HTML)
  --output-images DIR    이미지 저장 폴더 (기본: $OUTPUT_IMAGES)
  --output-labels DIR    라벨 저장 폴더 (기본: $OUTPUT_LABELS)
  --skip-generate        HTML 생성 단계 건너뛰기
  --skip-images          이미지 변환 단계 건너뛰기
  --skip-labels          라벨 생성 단계 건너뛰기
  -h, --help             도움말 표시

EXAMPLES:
  # 기본 실행 (100개 테이블, 각 1개 이미지)
  $0

  # 500개 테이블, 각 3개 이미지 버전 생성
  $0 --num-prompts 500 --images-per-file 3

  # 이미 생성된 HTML로 이미지만 재생성
  $0 --skip-generate --images-per-file 5

  # 라벨만 재생성
  $0 --skip-generate --skip-images

EOF
}

# ============================================
# 인자 파싱
# ============================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --num-prompts)
            NUM_PROMPTS="$2"
            shift 2
            ;;
        --images-per-file)
            IMAGES_PER_FILE="$2"
            shift 2
            ;;
        --color-probability)
            COLOR_PROBABILITY="$2"
            shift 2
            ;;
        --scale)
            SCALE="$2"
            shift 2
            ;;
        --output-html)
            OUTPUT_HTML="$2"
            shift 2
            ;;
        --output-images)
            OUTPUT_IMAGES="$2"
            shift 2
            ;;
        --output-labels)
            OUTPUT_LABELS="$2"
            shift 2
            ;;
        --skip-generate)
            SKIP_GENERATE=true
            shift
            ;;
        --skip-images)
            SKIP_IMAGES=true
            shift
            ;;
        --skip-labels)
            SKIP_LABELS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# ============================================
# 설정 출력
# ============================================
echo "============================================"
echo "  Synthetic Data Generation Pipeline"
echo "============================================"
echo ""
echo "Settings:"
echo "  - Num Prompts:       $NUM_PROMPTS"
echo "  - Images per File:   $IMAGES_PER_FILE"
echo "  - Color Probability: $COLOR_PROBABILITY"
echo "  - Scale:             ${SCALE}x"
echo ""
echo "Output Directories:"
echo "  - HTML:   $OUTPUT_HTML"
echo "  - Images: $OUTPUT_IMAGES"
echo "  - Labels: $OUTPUT_LABELS"
echo ""
echo "Skip Flags:"
echo "  - Skip Generate: $SKIP_GENERATE"
echo "  - Skip Images:   $SKIP_IMAGES"
echo "  - Skip Labels:   $SKIP_LABELS"
echo "============================================"
echo ""

# ============================================
# Step 1: HTML 테이블 생성 (Gemini API)
# ============================================
if [ "$SKIP_GENERATE" = false ]; then
    echo "[Step 1/3] Generating HTML tables with Gemini API..."
    echo "--------------------------------------------"
    
    python3 main_batch.py \
        --num-prompts "$NUM_PROMPTS" \
        --output-folder "$OUTPUT_HTML"
    
    echo ""
    echo "[Step 1/3] ✓ HTML generation completed!"
    echo ""
else
    echo "[Step 1/3] Skipped (--skip-generate)"
    echo ""
fi

# ============================================
# Step 2: HTML → 이미지 변환 (Augmentation)
# ============================================
if [ "$SKIP_IMAGES" = false ]; then
    echo "[Step 2/3] Converting HTML to images with augmentation..."
    echo "--------------------------------------------"
    
    python3 html2img.py \
        --input-dir "$OUTPUT_HTML" \
        --output-dir "$OUTPUT_IMAGES" \
        --count "$IMAGES_PER_FILE" \
        --color-probability "$COLOR_PROBABILITY" \
        --scale "$SCALE"
    
    echo ""
    echo "[Step 2/3] ✓ Image conversion completed!"
    echo ""
else
    echo "[Step 2/3] Skipped (--skip-images)"
    echo ""
fi

# ============================================
# Step 3: HTML 정제 → Label 생성
# ============================================
if [ "$SKIP_LABELS" = false ]; then
    echo "[Step 3/3] Extracting clean HTML labels..."
    echo "--------------------------------------------"
    
    python3 extract_table.py \
        --input-dir "$OUTPUT_HTML" \
        --output-dir "$OUTPUT_LABELS"
    
    echo ""
    echo "[Step 3/3] ✓ Label extraction completed!"
    echo ""
else
    echo "[Step 3/3] Skipped (--skip-labels)"
    echo ""
fi

# ============================================
# 완료 메시지
# ============================================
echo "============================================"
echo "  Pipeline Completed!"
echo "============================================"
echo ""
echo "Generated Files:"

if [ "$SKIP_GENERATE" = false ]; then
    HTML_COUNT=$(find "$OUTPUT_HTML" -name "*.html" 2>/dev/null | wc -l)
    echo "  - HTML files:  $HTML_COUNT (in $OUTPUT_HTML)"
fi

if [ "$SKIP_IMAGES" = false ]; then
    IMG_COUNT=$(find "$OUTPUT_IMAGES" -name "*.png" 2>/dev/null | wc -l)
    echo "  - Image files: $IMG_COUNT (in $OUTPUT_IMAGES)"
fi

if [ "$SKIP_LABELS" = false ]; then
    LABEL_COUNT=$(find "$OUTPUT_LABELS" -name "*.html" 2>/dev/null | wc -l)
    echo "  - Label files: $LABEL_COUNT (in $OUTPUT_LABELS)"
fi

echo ""
echo "============================================"
