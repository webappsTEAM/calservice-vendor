"""
Codebase Zipper Script
Compresses the project into a clean zip archive while intelligently excluding 
heavy installables/bloat (node_modules, .git, venvs, caches, wheels, builds, etc.) to minimize space,
while explicitly PRESERVING all .env configuration files.
"""

import argparse
import fnmatch
import os
from datetime import datetime
from pathlib import Path
import sys
import zipfile

# Determine project root directory (directory where this script is located)
SCRIPT_DIR = Path(__file__).resolve().parent
CUSTOMER_DIR = (SCRIPT_DIR / "Cus") if (SCRIPT_DIR / "Cus").exists() else (SCRIPT_DIR.parent / "Cus").resolve()
VENDOR_DIR = SCRIPT_DIR if (SCRIPT_DIR / "backend").exists() else (SCRIPT_DIR.parent / "Ven").resolve()

# Default directory patterns to exclude (installables, bloat, caches, build artifacts)
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".vite",
    ".cache",
    ".parcel-cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov",
    "coverage",
    ".gradle",
    ".dart_tool",
    "Pods",
    ".wheels",
    ".vscode",
    ".idea",
    ".gemini",
    ".claude",
    ".system_generated",
    "scratch",
    "mnt",
    "staticfiles",
    "Cus",
}

# Heavy image/media asset directories excluded when --exclude-assets is used
# These are catalog/mockup images that are NOT needed to run the codebase
ASSET_EXCLUDE_DIRS = {
    "ASSET IMAGES",   # backend/ASSET IMAGES  (~133 MB of service catalog images)
    "mockups",        # frontend/public/mockups (~156 MB of mockup images)
}

# Image/media file extensions excluded when --exclude-assets is used
ASSET_EXCLUDE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
    ".mp4", ".mov", ".avi", ".mkv", ".mp3", ".wav",
}

# Default file patterns to exclude (fnmatch patterns)
DEFAULT_EXCLUDE_FILES = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.whl",
    "*.log",
    "*.tmp",
    "*.bak",
    "*.swp",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.rar",
    "*.7z",
    "*.sqlite3",
    "*.apk",
    "*.aab",
    "*.ipa",
    "get-pip.py",
    "temp_booking*.jsx",
    "restore_log.txt",
    "test_workflow_results.log",
}


def parse_args():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Default output: dedicated Desktop\SEVO_Backups\ folder (separate from Cus/Ven)
    BACKUP_DIR = SCRIPT_DIR.parent / "SEVO_Backups"
    BACKUP_DIR.mkdir(exist_ok=True)
    default_output = BACKUP_DIR / f"calservices_archive_{timestamp}.zip"

    parser = argparse.ArgumentParser(
        description="Pack the codebase into a clean, lightweight zip archive excluding installables while preserving .env files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-o", "--output",
        default=str(default_output),
        help="Name or path of the output zip file",
    )
    parser.add_argument(
        "--target",
        choices=["customer", "vendor", "both", "all"],
        default="both",
        help="Which codebase to package: 'customer', 'vendor', or 'both'/'all' (default: both)",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Custom root directory to zip (overrides --target)",
    )
    parser.add_argument(
        "--include-env",
        dest="include_env",
        action="store_true",
        default=True,
        help="Explicitly include .env configuration files (Enabled by default)",
    )
    parser.add_argument(
        "--exclude-env",
        dest="include_env",
        action="store_false",
        help="Exclude .env configuration files from archive",
    )
    parser.add_argument(
        "--include-git",
        action="store_true",
        help="Include .git directory (Warning: significantly increases archive size)",
    )
    parser.add_argument(
        "--include-venv",
        action="store_true",
        help="Include virtual environments (.venv, venv, env)",
    )
    parser.add_argument(
        "--include-node-modules",
        action="store_true",
        help="Include node_modules folders (Warning: very large)",
    )
    parser.add_argument(
        "--exclude-assets",
        dest="exclude_assets",
        action="store_true",
        default=True,
        help="Exclude heavy image/media asset folders (ASSET IMAGES, mockups). Saves ~330 MB (default: True).",
    )
    parser.add_argument(
        "--include-assets",
        dest="exclude_assets",
        action="store_false",
        help="Include heavy image/media asset folders in archive.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be archived without creating the zip file",
    )
    return parser.parse_args()


def is_matching(filename: str, patterns: set) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def collect_files(
    root_dir: Path,
    exclude_dirs: set,
    exclude_files: set,
    include_env: bool,
    exclude_asset_exts: set,
    prefix: str = "",
):
    """Walk root_dir and collect (abs_path, arcname, file_size)."""
    collected = []
    uncompressed_bytes = 0
    skipped_dirs = 0
    skipped_files = 0
    env_files_included = 0

    for current_root, dirs, files in os.walk(root_dir):
        current_path = Path(current_root)

        # Filter out heavy/installable directories
        filtered_dirs = []
        for d in dirs:
            if d in exclude_dirs or is_matching(d, exclude_dirs):
                skipped_dirs += 1
            else:
                filtered_dirs.append(d)
        dirs[:] = filtered_dirs

        for f in files:
            file_path = current_path / f
            try:
                rel_path = file_path.relative_to(root_dir)
            except ValueError:
                continue

            # Skip existing zip files
            if f.endswith(".zip"):
                skipped_files += 1
                continue

            # Check if .env file — always honour include_env regardless of asset rules
            is_env_file = f == ".env" or f.startswith(".env.")
            if is_env_file:
                if not include_env:
                    skipped_files += 1
                    continue
                else:
                    env_files_included += 1
            else:
                # Skip heavy asset image/media extensions when requested
                if exclude_asset_exts:
                    fext = Path(f).suffix.lower()
                    if fext in exclude_asset_exts:
                        skipped_files += 1
                        continue

                # Check generic exclude patterns
                if is_matching(f, exclude_files):
                    skipped_files += 1
                    continue

            try:
                file_size = file_path.stat().st_size
            except OSError:
                file_size = 0

            arcname = f"{prefix}/{rel_path}".lstrip("/") if prefix else str(rel_path)
            collected.append((file_path, arcname, file_size))
            uncompressed_bytes += file_size

    return collected, uncompressed_bytes, skipped_dirs, skipped_files, env_files_included


def main():
    args = parse_args()
    output_path = Path(args.output).resolve()

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_files = set(DEFAULT_EXCLUDE_FILES)
    exclude_asset_exts: set = set()

    if args.include_git:
        exclude_dirs.discard(".git")
    if args.include_venv:
        exclude_dirs.difference_update({".venv", "venv", "env", "ENV"})
    if args.include_node_modules:
        exclude_dirs.discard("node_modules")
    if args.exclude_assets:
        exclude_dirs.update(ASSET_EXCLUDE_DIRS)
        exclude_asset_exts = set(ASSET_EXCLUDE_EXTS)

    print("\n" + "=" * 65)
    print("         SEVO / CalServices Codebase Packaging Utility")
    print("=" * 65)

    files_to_zip = []
    total_uncompressed = 0
    total_skipped_dirs = 0
    total_skipped_files = 0
    total_env_files = 0

    if args.root:
        custom_root = Path(args.root).resolve()
        if not custom_root.exists():
            print(f"[ERROR] Custom root directory does not exist: {custom_root}")
            sys.exit(1)
        print(f" Target Mode : Custom Root ({custom_root})")
        files, bytes_cnt, s_dirs, s_files, env_cnt = collect_files(
            custom_root, exclude_dirs, exclude_files, args.include_env, exclude_asset_exts, prefix=""
        )
        files_to_zip.extend(files)
        total_uncompressed += bytes_cnt
        total_skipped_dirs += s_dirs
        total_skipped_files += s_files
        total_env_files += env_cnt
    elif args.target in ("both", "all"):
        print(f" Target Mode : Both Codebases (Customer + Vendor)")
        if CUSTOMER_DIR.exists():
            files, bytes_cnt, s_dirs, s_files, env_cnt = collect_files(
                CUSTOMER_DIR, exclude_dirs, exclude_files, args.include_env, exclude_asset_exts, prefix="Customer"
            )
            files_to_zip.extend(files)
            total_uncompressed += bytes_cnt
            total_skipped_dirs += s_dirs
            total_skipped_files += s_files
            total_env_files += env_cnt
        if VENDOR_DIR.exists():
            files, bytes_cnt, s_dirs, s_files, env_cnt = collect_files(
                VENDOR_DIR, exclude_dirs, exclude_files, args.include_env, exclude_asset_exts, prefix="Vendor"
            )
            files_to_zip.extend(files)
            total_uncompressed += bytes_cnt
            total_skipped_dirs += s_dirs
            total_skipped_files += s_files
            total_env_files += env_cnt
    elif args.target == "vendor":
        print(f" Target Mode : Vendor Codebase ({VENDOR_DIR})")
        if not VENDOR_DIR.exists():
            print(f"[ERROR] Vendor directory does not exist: {VENDOR_DIR}")
            sys.exit(1)
        files, bytes_cnt, s_dirs, s_files, env_cnt = collect_files(
            VENDOR_DIR, exclude_dirs, exclude_files, args.include_env, exclude_asset_exts, prefix=""
        )
        files_to_zip.extend(files)
        total_uncompressed += bytes_cnt
        total_skipped_dirs += s_dirs
        total_skipped_files += s_files
        total_env_files += env_cnt
    else:  # customer
        print(f" Target Mode : Customer Codebase ({CUSTOMER_DIR})")
        files, bytes_cnt, s_dirs, s_files, env_cnt = collect_files(
            CUSTOMER_DIR, exclude_dirs, exclude_files, args.include_env, exclude_asset_exts, prefix=""
        )
        files_to_zip.extend(files)
        total_uncompressed += bytes_cnt
        total_skipped_dirs += s_dirs
        total_skipped_files += s_files
        total_env_files += env_cnt

    print(f" Output Zip  : {output_path}")
    print(f" .env Files  : {'Included' if args.include_env else 'Excluded'} ({total_env_files} .env file(s) found)")
    print(f" Excluded    : node_modules, venv, .git, caches, dist, build, wheels")
    if args.exclude_assets:
        print(f" Assets      : EXCLUDED (ASSET IMAGES, mockups, .jpg/.png/.webp etc.) -- saves ~330 MB")
    else:
        print(f" Assets      : Included (use --exclude-assets to skip images and save ~330 MB)")
    print(f" Dry Run     : {'Enabled' if args.dry_run else 'Disabled'}")
    print("-" * 65)
    print(f" Files Found  : {len(files_to_zip):,} files to pack")
    print(f" Source Size  : {format_size(total_uncompressed)}")
    print(f" Filtered Out : {total_skipped_dirs:,} folders, {total_skipped_files:,} files")
    print("-" * 65)

    if args.dry_run:
        print("\n [Preview] Key files included (sample):")
        # Show .env files specifically in the preview
        env_samples = [f for f in files_to_zip if ".env" in f[1]]
        if env_samples:
            print("   -> Environment configs included:")
            for _, arcname, size in env_samples:
                print(f"      * {arcname} ({format_size(size)})")
        print("   -> Sample codebase files:")
        for idx, (_, rel_path, size) in enumerate(files_to_zip[:15], start=1):
            print(f"      {idx:2d}. {rel_path} ({format_size(size)})")
        print("\n [OK] Dry run completed. No archive written.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(" [1/2] Compressing into zip archive...")
    start_time = datetime.now()

    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        total = len(files_to_zip)
        step = max(1, total // 10)
        for idx, (abs_path, arcname, _) in enumerate(files_to_zip, start=1):
            zipf.write(abs_path, arcname=arcname)
            if idx % step == 0 or idx == total:
                pct = (idx / total) * 100
                print(f"   -> Progress: {pct:5.1f}% ({idx:,}/{total:,} files)")

    elapsed = (datetime.now() - start_time).total_seconds()
    zip_size = output_path.stat().st_size
    saved_pct = ((total_uncompressed - zip_size) / total_uncompressed * 100) if total_uncompressed > 0 else 0

    print(" [2/2] Done!")
    print("=" * 65)
    print("                    Archive Summary")
    print("=" * 65)
    print(f" Archive Name    : {output_path.name}")
    print(f" Saved Location  : {output_path}")
    print(f" Uncompressed    : {format_size(total_uncompressed)}")
    print(f" Compressed Size : {format_size(zip_size)}")
    print(f" Space Reduction : {saved_pct:.1f}% saved")
    print(f" .env Files      : {total_env_files} included")
    print(f" Total Duration  : {elapsed:.2f}s")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
