import os
import re
import shutil
import logging
from pathlib import Path
from datetime import datetime
from threading import Lock

# 로깅 설정 (터미널 출력 및 파일 저장 동시 진행)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("diagnosis_result.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)


class ProjectDiagnoser:
    """프로젝트 내의 문제점(중복 폴더, 20바이트 에러 파일)을 안전하게 진단 및 청소하는 클래스"""

    def __init__(self, target_dir: str):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.allowed_root = (self.repo_root / 'uploads' / 'projects').resolve()
        self.target_dir = Path(target_dir).resolve()
        self.quarantine_root = (
            self.repo_root / 'archive' / 'recovery_quarantine'
        )
        # 🚨 절대 건드리면 안 되는 보호 폴더 목록
        self.exclude_dirs = {
            'frontend', 'node_modules', '.next', '.git',
            '.venv', 'venv', '__pycache__', 'dist', 'build',
            'Lib', 'Scripts', 'site-packages', 'site-packaages'
        }
        self._ensure_safe_target()

    def _ensure_safe_target(self):
        # 한국어 안전 가드: 업로드 프로젝트 루트 밖은 진단만 해도 위험하므로 즉시 차단한다.
        try:
            self.target_dir.relative_to(self.allowed_root)
        except ValueError as exc:
            raise ValueError(
                "진단 대상이 허용 범위를 벗어났습니다: "
                f"{self.target_dir} (허용 범위: {self.allowed_root})"
            ) from exc

    def scan_duplicate_folders(self):
        """이름 끝에 (1), _1 등이 붙은 중복 생성 의심 폴더 스캔"""
        logging.info("🔍 중복 폴더 스캔 시작...")
        duplicates = []
        pattern = re.compile(r'(.+)[\(_-]\d+[\)]?$')

        for root, dirs, files in os.walk(self.target_dir):
            # 보호 폴더는 하위 탐색에서 제외
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for d in dirs:
                if pattern.match(d):
                    duplicates.append(os.path.join(root, d))

        if duplicates:
            logging.warning(f"⚠️ 중복 의심 폴더 {len(duplicates)}개 발견:")
            for dup in duplicates:
                logging.warning(f"  - {dup}")
        else:
            logging.info("✅ 중복 폴더가 발견되지 않았습니다.")

    def clean_error_files(self, apply_changes: bool = False):
        """오케스트레이터가 생성한 20바이트(또는 0바이트) 에러 깡통 파일만 타겟팅하여 격리"""
        mode_label = "실제 격리" if apply_changes else "드라이런"
        logging.info(f"🧹 20바이트 에러 깡통 파일 스캔 시작... (모드: {mode_label})")
        truncated_count = 0
        quarantined_count = 0
        session_name = datetime.now().strftime('%Y%m%d_%H%M%S')
        quarantine_session_dir = self.quarantine_root / session_name

        for root, dirs, files in os.walk(self.target_dir):
            # 보호 폴더는 하위 탐색에서 제외
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for f in files:
                if f.endswith(('.py', '.js', '.ts', '.java', '.cpp')):
                    filepath = Path(root) / f
                    try:
                        size = filepath.stat().st_size
                        # 한국어 안전 기준: 허용 루트 내부의 명백한 깡통 파일만 격리 대상으로 본다.
                        if size == 20 or size == 0:
                            truncated_count += 1
                            if apply_changes:
                                relative_path = filepath.relative_to(
                                    self.allowed_root
                                )
                                quarantine_path = (
                                    quarantine_session_dir / relative_path
                                )
                                quarantine_path.parent.mkdir(
                                    parents=True,
                                    exist_ok=True,
                                )
                                shutil.move(
                                    str(filepath),
                                    str(quarantine_path),
                                )
                                quarantined_count += 1
                                logging.warning(
                                    "📦 [격리 완료] 에러 파일: "
                                    f"{filepath} -> {quarantine_path} "
                                    f"(크기: {size} bytes)"
                                )
                            else:
                                logging.warning(
                                    "🔎 [드라이런] 격리 대상 파일: "
                                    f"{filepath} (크기: {size} bytes)"
                                )
                    except Exception as e:
                        logging.error(f"❌ 파일 확인/격리 중 에러 ({filepath}): {e}")

        if truncated_count > 0:
            if apply_changes:
                logging.info(
                    "🏁 청소 완료: 총 "
                    f"{truncated_count}개의 깡통 파일 중 "
                    f"{quarantined_count}개를 격리했습니다."
                )
            else:
                logging.info(
                    "🏁 드라이런 완료: 총 "
                    f"{truncated_count}개의 격리 후보를 발견했습니다."
                )
        else:
            logging.info("✅ 20바이트 에러 파일이 발견되지 않았습니다.")

    def run_full_diagnosis(self, apply_changes: bool = False):
        mode_label = "실제 격리" if apply_changes else "드라이런"
        logging.info(f"🚀 프로젝트 전체 안전 진단 및 청소 시작 (모드: {mode_label})")
        self.scan_duplicate_folders()
        self.clean_error_files(apply_changes=apply_changes)
        logging.info("🏁 프로젝트 진단 및 청소 완료")


class SafeOrchestratorFS:
    """멀티 오케스트레이터 환경을 위한 스레드 안전(Thread-safe) 파일/폴더 관리기"""

    _folder_lock = Lock()
    _file_locks = {}
    _file_locks_lock = Lock()

    @classmethod
    def get_file_lock(cls, filepath: str):
        with cls._file_locks_lock:
            if filepath not in cls._file_locks:
                cls._file_locks[filepath] = Lock()
            return cls._file_locks[filepath]

    @classmethod
    def safe_create_folder(cls, folder_path: str):
        """레이스 컨디션을 방지하는 안전한 폴더 생성"""
        with cls._folder_lock:
            path = Path(folder_path)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logging.info(f"📁 폴더 생성 완료: {folder_path}")
                except Exception as e:
                    logging.error(f"❌ 폴더 생성 실패 ({folder_path}): {e}")
            else:
                pass  # 이미 존재하는 경우 조용히 넘어감

    @classmethod
    def safe_write_code(
        cls,
        filepath: str,
        code_content: str,
        min_expected_length: int = 150,
    ):
        """파일 덮어쓰기 충돌 및 코드 짤림 방지를 위한 안전한 저장"""
        # 에러 문자열 등 너무 짧은 코드가 들어오면 저장을 거부함
        if len(code_content.encode('utf-8')) < min_expected_length:
            logging.error(
                "❌ 코드 생성 실패 (길이 미달 거부) - 파일명: "
                f"{os.path.basename(filepath)}"
            )
            return False

        lock = cls.get_file_lock(filepath)
        with lock:
            try:
                cls.safe_create_folder(os.path.dirname(filepath))
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(code_content)
                logging.info(
                    "💾 코드 정상 저장 완료 "
                    f"({len(code_content.encode('utf-8'))} bytes): "
                    f"{filepath}"
                )
                return True
            except Exception as e:
                logging.error(f"❌ 코드 저장 중 에러 발생 ({filepath}): {e}")
                return False


# ==========================================
# 실행 부분
# ==========================================
if __name__ == "__main__":
    PROJECT_ROOT = (
        Path(__file__).resolve().parent.parent / 'uploads' / 'projects'
    )
    APPLY_CHANGES = os.getenv('ORCHESTRATOR_MANAGER_APPLY') == '1'

    diagnoser = ProjectDiagnoser(PROJECT_ROOT)
    diagnoser.run_full_diagnosis(apply_changes=APPLY_CHANGES)
