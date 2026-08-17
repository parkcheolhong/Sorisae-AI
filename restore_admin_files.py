import os
import shutil
import sys

source_dir = r"c:\Users\WORK\source\repos\parkcheolhong\codeAI\tmp\codeAI_2026_04_11_extracted\codeAI\frontend\frontend"
target_dir = r"c:\Users\WORK\source\repos\parkcheolhong\codeAI\frontend\frontend"


def _abort(message: str) -> None:
    print(f"[restore_admin_files] BLOCKED: {message}")
    sys.exit(1)


def _ensure_isolated_paths() -> None:
    allow_flag = os.environ.get('ALLOW_PROD_RESTORE', '').strip().lower()
    if allow_flag not in {'1', 'true', 'yes'}:
        _abort('Set ALLOW_PROD_RESTORE=1 to run this script explicitly.')

    normalized_source = os.path.normpath(source_dir).lower()
    normalized_target = os.path.normpath(target_dir).lower()

    if 'admin_self_experiments' in normalized_source:
        _abort(f'Experimental source path is not allowed: {source_dir}')

    if 'uploads\\tmp' in normalized_source:
        _abort(f'uploads/tmp source path is not allowed: {source_dir}')

    if not normalized_source.endswith(os.path.normpath('tmp\\codeAI_2026_04_11_extracted\\codeAI\\frontend\\frontend').lower()):
        _abort(f'Unexpected restore source root: {source_dir}')

    if not normalized_target.endswith(os.path.normpath('codeAI\\frontend\\frontend').lower()):
        _abort(f'Unexpected restore target root: {target_dir}')


_ensure_isolated_paths()

# We ONLY want to forcefully overwrite files in these directories
target_folders = [
    "lib",
    "shared",
    "components/admin",
    "app/admin"
]

print(f"Forcefully restoring admin folders from:\n{source_dir}\nto\n{target_dir}\n")

copied_count = 0

for folder in target_folders:
    src_folder = os.path.join(source_dir, folder)
    tgt_folder = os.path.join(target_dir, folder)
    
    if os.path.exists(src_folder):
        for root, dirs, files in os.walk(src_folder):
            rel_path = os.path.relpath(root, src_folder)
            target_root = os.path.join(tgt_folder, rel_path)
            
            if not os.path.exists(target_root):
                os.makedirs(target_root)
                
            for file in files:
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_root, file)
                
                # Force copy (overwrite)
                shutil.copy2(source_file, target_file)
                print(f"Overwrote: {os.path.join(folder, rel_path, file)}")
                copied_count += 1

print(f"\nSuccessfully forcefully restored {copied_count} files in admin/shared folders.")
