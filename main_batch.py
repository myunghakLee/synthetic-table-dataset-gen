# pip install google-genai

from typing import Dict, List, Optional
from pathlib import Path
import argparse
import logging
import json
import time
import re

from google.genai import types
from google import genai

from make_prompt import generate_weighted_prompt


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


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# 외부 라이브러리 로그 레벨 조정
for name in ("google", "httpx", "httpcore"):
    logging.getLogger(name).setLevel(logging.WARNING)


class GeminiBatchQAGenerator:
    """텍스트 프롬프트를 입력받아 텍스트 응답을 생성하는 Batch 처리기"""
    
    def __init__(
        self,
        api_key_file: str,
        output_folder: str,
        model: str,
        top_p: float,
        top_k: Optional[int],
        temperature: float,
        num_prompts: int,
        max_attempts_count: int,
        **kwargs
    ):
        self.output_folder = Path(output_folder)
        self.model = model
        self.top_p = top_p
        self.top_k = top_k
        self.temperature = temperature
        self.num_prompts = num_prompts
        self.max_attempts_count = max_attempts_count
        
        self.api_key = self._load_api_key(api_key_file)
        self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})

    def _load_api_key(self, file_path: str) -> str:
        p = Path(file_path)
        try:
            return p.read_text(encoding="utf-8-sig").strip()
        except Exception:
            return p.read_text(encoding="utf-16").strip()

    def _make_gen_config_dict(self) -> Dict:
        """생성 설정 딕셔너리 생성"""
        cfg = {
            "response_modalities": ["TEXT"],
            "temperature": float(self.temperature),
            "top_p": float(self.top_p) if self.top_p else None,
            "top_k": int(self.top_k) if self.top_k else None,
        }
        return {k: v for k, v in cfg.items() if v is not None}

    def generate_prompts(self) -> List[str]:
        """make_prompt.py를 사용하여 프롬프트 목록 생성"""
        prompts = []
        for _ in range(self.num_prompts):
            prompt = generate_weighted_prompt()
            prompts.append(prompt)
        log.info(f"[*] Generated {len(prompts)} prompts")
        return prompts

    def create_batch_file(
        self,
        prompts: List[str],
        output_filename: str = "batch_requests.jsonl"
    ) -> str:
        """프롬프트 목록으로 Batch 요청 JSONL 파일 생성"""
        valid_count = 0
        
        with open(output_filename, "w", encoding="utf-8") as f:
            for idx, prompt in enumerate(prompts):
                for attempt in range(self.max_attempts_count):
                    key = f"prompt_{idx:04d}|{attempt}"
                    
                    request_body = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": prompt}]
                            }
                        ],
                        "generation_config": self._make_gen_config_dict(),
                    }
                    
                    request_data = {
                        "key": key,
                        "request": request_body
                    }
                    
                    f.write(json.dumps(request_data, ensure_ascii=False) + "\n")
                    valid_count += 1
        
        log.info(f"[*] Created batch file: {output_filename} (Requests: {valid_count})")
        return output_filename

    def run_batch_process(self, jsonl_path: str) -> Optional[str]:
        """Batch Job 실행"""
        batch_input_file = None
        try:
            # 1. JSONL 파일 업로드
            batch_input_file = self.client.files.upload(
                file=jsonl_path,
                config={'mime_type': 'application/json'}
            )
            
            # 2. Batch Job 생성
            job = self.client.batches.create(
                model=self.model,
                src=batch_input_file.name,
                config=types.CreateBatchJobConfig(
                    display_name=f"qa_batch_{int(time.time())}"
                )
            )
            log.info(f"[*] Batch Job Started! ID: {job.name.split('/')[-1]}")
            
        except Exception as e:
            log.error(f"Failed to submit Batch Job: {e}")
            if batch_input_file:
                try:
                    self.client.files.delete(name=batch_input_file.name)
                except Exception:
                    pass
            return None

        # 3. 상태 대기 (Polling)
        while True:
            try:
                job = self.client.batches.get(name=job.name)
                state_name = job.state.name if hasattr(job.state, 'name') else str(job.state)
                log.info(f"    Status: {state_name}")
                
                if state_name == "JOB_STATE_SUCCEEDED":
                    break
                elif state_name in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
                    log.error(f"[!] Job Failed: {job.error}")
                    break
            except Exception:
                pass
            time.sleep(30)

        # 4. 사용이 끝난 JSONL 파일 삭제
        if batch_input_file:
            try:
                self.client.files.delete(name=batch_input_file.name)
                log.info("    🗑️ Batch input JSONL file deleted from cloud.")
            except Exception as e:
                log.warning(f"Failed to delete JSONL file: {e}")

        # 5. 결과 반환
        if hasattr(job, 'dest') and job.dest and hasattr(job.dest, 'file_name'):
            return job.dest.file_name
        return None

    def download_and_save_results(self, output_file_uri: str, prompts: List[str]) -> int:
        """결과 다운로드 및 저장 (파일명 숫자 자동 증가 방식, 프롬프트도 함께 저장)"""
        log.info("[*] Downloading results...")
        content = self.client.files.download(file=output_file_uri)
        output_data = content.decode("utf-8")
        
        # 디버깅용 저장
        debug_file = "debug_batch_results.jsonl"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(output_data)
        log.info(f"[*] Raw response saved to {debug_file}")

        self.output_folder.mkdir(parents=True, exist_ok=True)
        success_count = 0
        
        # -------------------------------------------------------
        # [수정] 현재 폴더에서 가장 높은 번호 찾기 (이어쓰기 준비)
        # -------------------------------------------------------
        max_idx = -1
        existing_files = list(self.output_folder.glob("prompt_*.html"))
        
        for f in existing_files:
            try:
                # 'prompt_0012.html' -> '0012' -> 12 추출
                num_part = f.stem.split('_')[-1] # prompt_XXXX 형태 가정
                if num_part.isdigit():
                    idx = int(num_part)
                    if idx > max_idx:
                        max_idx = idx
            except Exception:
                pass
        
        # 다음 저장할 번호 시작점 (예: 파일이 없으면 0, 9번까지 있으면 10)
        current_save_idx = max_idx + 1
        # -------------------------------------------------------

        for line in output_data.strip().split("\n"):
            try:
                res = json.loads(line)
                custom_id = res.get("custom_id") or res.get("key")
                
                if not custom_id:
                    continue

                # 응답 파싱
                response_val = res.get("response", {})
                
                # 에러 체크
                if "status_code" in response_val and response_val["status_code"] != 200:
                    log.error(f"[!] API Error: {response_val}")
                    continue

                body = response_val.get("body", response_val)
                candidates = body.get("candidates", [])
                
                if not candidates:
                    continue
                
                for cand in candidates:
                    parts = cand.get("content", {}).get("parts", [])
                    for part in parts:
                        if "text" in part:
                            # ---------------------------------------------------
                            # [수정] 빈 번호를 찾아서 저장 + 프롬프트도 함께 저장
                            # ---------------------------------------------------
                            txt_path = self.output_folder / f"prompt_{current_save_idx:04d}.html"
                            
                            # 혹시 중간에 파일이 끼어있을 경우를 대비해 확실한 빈 번호 찾기
                            while txt_path.exists():
                                current_save_idx += 1
                                txt_path = self.output_folder / f"prompt_{current_save_idx:04d}.html"
                            
                            # HTML 파일 저장 (마크다운 코드블록 제거)
                            html_content = clean_markdown_codeblocks(part["text"])
                            with open(txt_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                            
                            # 해당 프롬프트도 txt 파일로 저장
                            try:
                                # custom_id에서 원본 프롬프트 인덱스 추출 (prompt_0001|0 -> 1)
                                prompt_idx = int(custom_id.split('|')[0].split('_')[-1])
                                if 0 <= prompt_idx < len(prompts):
                                    prompt_txt_path = self.output_folder / f"prompt_{current_save_idx:04d}.txt"
                                    with open(prompt_txt_path, "w", encoding="utf-8") as f:
                                        f.write(prompts[prompt_idx])
                                    log.info(f"    [Saved] {txt_path.name} + {prompt_txt_path.name}")
                                else:
                                    log.info(f"    [Saved] {txt_path.name} (prompt index out of range)")
                            except Exception as e:
                                log.warning(f"    [Saved] {txt_path.name} (failed to save prompt: {e})")
                            
                            success_count += 1
                            current_save_idx += 1 # 다음 저장을 위해 번호 증가
                            # ---------------------------------------------------

            except Exception as e:
                log.error(f"Error parsing line: {e}")
                
        return success_count

def main():
    parser = argparse.ArgumentParser(description="Gemini Batch QA Generator")
    parser.add_argument("--output-folder", default="GeneratedHTMLs", help="Directory to save output files")
    parser.add_argument("--api-key-file", default="./gemini_api_key.txt")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--num-prompts", type=int, default=100, help="Number of prompts to generate")
    parser.add_argument("--max-attempts-count", type=int, default=1)

    args = parser.parse_args()

    generator = GeminiBatchQAGenerator(**vars(args))
    
    try:
        # 1. 프롬프트 생성
        prompts = generator.generate_prompts()
        
        # 2. 프롬프트 목록을 파일로 저장 (확인용)
        prompts_file = Path(args.output_folder) / "generated_prompts.txt"
        prompts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(prompts_file, "w", encoding="utf-8") as f:
            for i, p in enumerate(prompts):
                f.write(f"=== Prompt {i:04d} ===\n{p}\n\n")
        log.info(f"[*] Prompts saved to {prompts_file}")
        
        # 3. Batch 파일 생성
        jsonl_path = generator.create_batch_file(prompts)
        
        # 4. Batch 실행
        result_uri = generator.run_batch_process(jsonl_path)
        
        # 5. 결과 다운로드 및 저장
        if result_uri:
            count = generator.download_and_save_results(result_uri, prompts)
            log.info(f"\n[*] Batch Finished. Success: {count}/{len(prompts)}")
        else:
            log.error("[!] Batch Process Failed.")
            
    except KeyboardInterrupt:
        print("\n[!] Stopped by user.")
    except Exception as e:
        log.error(f"\n[!] Unexpected Error: {e}")
        raise


if __name__ == "__main__":
    main()