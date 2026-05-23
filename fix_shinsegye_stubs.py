"""
Fix broken placeholder .py files in backend/services/shinsegye/projects/
These files contain only a relative path string (e.g. ../../../filename.py)
which is invalid Python syntax. Replace them with real Python from external_migrations.
"""
import os
import shutil

SRC_BASE = r"tmp\external_migrations\run_all_shinsegye.py"
UPSTREAM_BASE = r"tmp\external_migrations\upstream_sources\run_all_shinsegye.py-main-20260505"
PROJ_BASE = r"backend\services\shinsegye\projects"


def main():
    fixed = 0
    skipped = []

    for root, dirs, files in os.walk(PROJ_BASE):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            path = os.path.join(root, fname)
            with open(path, "rb") as fh:
                raw = fh.read()
            # Detect if this is a placeholder: short file starting with '..'
            try:
                content = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                content = raw.decode("latin-1").strip()

            if not content.startswith(".."):
                continue  # already real Python

            # Try to find the original file
            ref_name = os.path.basename(content)
            candidates = [
                os.path.join(SRC_BASE, ref_name),
                os.path.join(UPSTREAM_BASE, ref_name),
            ]
            found = None
            for c in candidates:
                if os.path.exists(c):
                    found = c
                    break

            if found:
                shutil.copy2(found, path)
                fixed += 1
            else:
                skipped.append(ref_name)

    print(f"Fixed: {fixed}")
    if skipped:
        print(f"Missing originals ({len(skipped)}):")
        for s in sorted(set(skipped)):
            print(f"  {s}")
    else:
        print("All files restored successfully.")


if __name__ == "__main__":
    main()
