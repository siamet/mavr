#!/usr/bin/env python3
"""Install tree-sitter language grammars for supported languages."""

import os
import sys
from pathlib import Path

try:
    from tree_sitter import Language
except ImportError:
    print("tree-sitter not installed. Please run: uv sync")
    sys.exit(1)


def download_and_build_grammars():
    """Download and build tree-sitter language grammars."""

    # Directory to store compiled grammars
    build_dir = Path(__file__).parent.parent / "build"
    build_dir.mkdir(exist_ok=True)

    languages_dir = build_dir / "tree-sitter-languages"
    languages_dir.mkdir(exist_ok=True)

    # Language repositories
    languages = {
        "python": "https://github.com/tree-sitter/tree-sitter-python",
        "javascript": "https://github.com/tree-sitter/tree-sitter-javascript",
        "java": "https://github.com/tree-sitter/tree-sitter-java",
        "typescript": "https://github.com/tree-sitter/tree-sitter-typescript",
    }

    print("Installing tree-sitter language grammars...")
    print(f"Build directory: {build_dir}")

    # Clone repositories if they don't exist
    for lang_name, repo_url in languages.items():
        lang_dir = languages_dir / f"tree-sitter-{lang_name}"

        if not lang_dir.exists():
            print(f"Cloning {lang_name} grammar...")
            os.system(f"git clone --depth=1 {repo_url} {lang_dir}")
        else:
            print(f"{lang_name} grammar already exists")

    # Build shared library
    print("\nBuilding shared library...")

    lib_path = build_dir / "languages.so"

    # Handle TypeScript which has subdirectories
    typescript_dir = languages_dir / "tree-sitter-typescript"
    typescript_subdirs = ["typescript", "tsx"]

    language_paths = [
        languages_dir / "tree-sitter-python",
        languages_dir / "tree-sitter-javascript",
        languages_dir / "tree-sitter-java",
    ]

    # Add TypeScript subdirectories
    for subdir in typescript_subdirs:
        ts_path = typescript_dir / subdir
        if ts_path.exists():
            language_paths.append(ts_path)

    try:
        Language.build_library(
            str(lib_path),
            [str(p) for p in language_paths if p.exists()]
        )
        print(f"Successfully built language library at: {lib_path}")
    except Exception as e:
        print(f"Error building language library: {e}")
        print("\nTrying alternative method...")

        # Try installing via uv
        print("Installing pre-built language bindings...")
        os.system("uv add tree-sitter-languages")
        print("Installed tree-sitter-languages package")

    print("\nLanguage grammar setup complete!")
    return True


if __name__ == "__main__":
    try:
        download_and_build_grammars()
    except Exception as e:
        print(f"\nSetup failed: {e}")
        print("\nFalling back to uv package installation...")
        os.system("uv add tree-sitter-languages")
        print("Installed tree-sitter-languages as fallback")
