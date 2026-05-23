import sys
from pathlib import Path


def run_round(tag: str, text: str) -> None:
    root = Path(__file__).resolve().parents[2]
    src = root / "addons" / "shinsegye_interpreter" / "src"
    sys.path.insert(0, str(src))

    from sorisae_interpreter import SorisaeInterpreter

    interp = SorisaeInterpreter()
    print(f"{tag}_INIT_OK", type(interp).__name__)
    print(f"{tag}_TRANSLATE", interp.quick_translate(text, "ko", "en"))


if __name__ == "__main__":
    run_round("ROUND1", "안녕하세요")
    run_round("ROUND2", "감사합니다")
