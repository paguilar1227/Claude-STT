"""File index generation — scans a project directory for source files.

Supports full indexing via os.walk and incremental updates via git delta.
Index cache is stored externally (~/.claude-stt/indexes/) to avoid
writing anything to the repo.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import logging

logger = logging.getLogger(__name__)

# Extensions to include in the index
SOURCE_EXTENSIONS = {
    ".cs", ".csproj", ".sln",
    ".ts", ".tsx", ".js", ".jsx",
    ".py", ".pyw",
    ".json", ".yaml", ".yml",
    ".xml", ".config",
    ".md", ".txt",
    ".sql",
    ".sh", ".ps1", ".psm1", ".cmd", ".bat",
    ".css", ".scss", ".html",
    ".toml", ".env", ".ini",
    ".props", ".targets",
    ".resx", ".ruleset",
    ".dockerfile",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules", ".git", "dist", "__pycache__", ".next", "build",
    "bin", "obj", ".vs", ".vscode", "packages", ".nuget",
    "TestResults", "BenchmarkDotNet.Artifacts",
    ".worktrees", "artifacts", "publish", "out",
    ".terraform", ".cache", "coverage",
}

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".claude-stt", "indexes")
CACHE_MAX_AGE_HOURS = 24


def _cache_key(project_root: str) -> str:
    """Generate a stable hash for a project root path."""
    normalized = os.path.abspath(project_root).replace("\\", "/").lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _cache_path(project_root: str) -> str:
    """Get the cache file path for a project."""
    return os.path.join(CACHE_DIR, f"{_cache_key(project_root)}.json")


def find_repo_root(start_dir: str | None = None) -> str | None:
    """Walk up from start_dir to find the nearest .git directory.

    Returns the repo root path, or None if not inside a git repo.
    """
    current = os.path.abspath(start_dir or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def build_index(project_root: str, extensions: set[str] | None = None) -> list[str]:
    """Walk the project directory and return a list of relative file paths.

    Args:
        project_root: Root directory to scan.
        extensions: Set of file extensions to include (with dot prefix).
                   Defaults to SOURCE_EXTENSIONS.

    Returns:
        Sorted list of relative file paths.
    """
    if extensions is None:
        extensions = SOURCE_EXTENSIONS

    t0 = time.monotonic()
    files = []
    extensionless_names = {"dockerfile", "makefile", ".gitignore", ".editorconfig"}

    for dirpath, dirnames, filenames in os.walk(project_root):
        # Prune skip directories in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            _, ext = os.path.splitext(fname)
            is_source = ext.lower() in extensions
            is_special = fname.lower() in extensionless_names

            if is_source or is_special:
                rel = os.path.relpath(
                    os.path.join(dirpath, fname), project_root
                ).replace("\\", "/")
                files.append(rel)

    files = sorted(set(files))
    elapsed = time.monotonic() - t0
    logger.info(f"Indexed {len(files)} files in {elapsed*1000:.0f}ms")
    return files


def _has_extension(filepath: str, extensions: set[str]) -> bool:
    """Check if a file has one of the tracked extensions."""
    _, ext = os.path.splitext(filepath)
    if ext.lower() in extensions:
        return True
    basename = os.path.basename(filepath).lower()
    return basename in {"dockerfile", "makefile", ".gitignore", ".editorconfig"}


def git_delta_update(
    project_root: str,
    cached_files: list[str],
    extensions: set[str] | None = None,
) -> list[str] | None:
    """Update a cached file list using git to detect changes.

    Returns the updated file list, or None if git delta isn't available
    (caller should fall back to full index).
    """
    if extensions is None:
        extensions = SOURCE_EXTENSIONS

    try:
        # Get files that changed since last commit + untracked new files
        changed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=project_root,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=10,
            cwd=project_root,
        )
        deleted = subprocess.run(
            ["git", "ls-files", "--deleted"],
            capture_output=True, text=True, timeout=10,
            cwd=project_root,
        )

        if changed.returncode != 0:
            return None

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    t0 = time.monotonic()

    file_set = set(cached_files)

    # Remove deleted files
    for f in deleted.stdout.strip().splitlines():
        f = f.strip().replace("\\", "/")
        file_set.discard(f)

    # Add new/changed files (if they have tracked extensions)
    for f in changed.stdout.strip().splitlines() + untracked.stdout.strip().splitlines():
        f = f.strip().replace("\\", "/")
        if not f:
            continue
        full_path = os.path.join(project_root, f)
        if os.path.isfile(full_path) and _has_extension(f, extensions):
            file_set.add(f)
        elif not os.path.isfile(full_path):
            file_set.discard(f)

    result = sorted(file_set)
    elapsed = time.monotonic() - t0
    delta_count = len(result) - len(cached_files)
    logger.info(f"Git delta update: {delta_count:+d} files in {elapsed*1000:.0f}ms")
    return result


def save_cache(project_root: str, files: list[str]):
    """Save the file index to the external cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = {
        "project_root": os.path.abspath(project_root).replace("\\", "/"),
        "timestamp": time.time(),
        "file_count": len(files),
        "files": files,
    }
    path = _cache_path(project_root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    logger.debug(f"Saved index cache ({len(files)} files) to {path}")


def load_cache(project_root: str) -> tuple[list[str], float] | None:
    """Load a cached index for the given project root.

    Returns (file_list, timestamp) or None if no cache exists.
    """
    path = _cache_path(project_root)
    if not os.path.exists(path):
        return None

    try:
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
        files = cache["files"]
        ts = cache["timestamp"]
        logger.debug(f"Loaded cached index ({len(files)} files) from {path}")
        return files, ts
    except (json.JSONDecodeError, KeyError, OSError):
        logger.warning(f"Corrupted cache at {path}, will rebuild")
        return None


def smart_load(project_root: str) -> tuple[list[str], bool]:
    """Load the best available index: cache + git delta, or full rebuild.

    Returns:
        (file_list, is_from_cache) — is_from_cache=True means it loaded
        instantly and a background refresh may still be needed.
    """
    cached = load_cache(project_root)

    if cached is not None:
        files, ts = cached
        age_hours = (time.time() - ts) / 3600

        if age_hours < CACHE_MAX_AGE_HOURS:
            # Try git delta for quick update
            updated = git_delta_update(project_root, files)
            if updated is not None:
                save_cache(project_root, updated)
                return updated, True
            # Git delta failed, cache is still usable
            return files, True

        logger.info(f"Cache is {age_hours:.0f}h old, rebuilding")

    # No cache or stale — full rebuild
    files = build_index(project_root)
    save_cache(project_root, files)
    return files, False


# Keep backward compatibility for tests
def save_index(files: list[str], path: str):
    """Write the file index to a plain text file."""
    with open(path, "w", encoding="utf-8") as f:
        for filepath in files:
            f.write(filepath + "\n")


def load_index(path: str) -> list[str]:
    """Load a file index from a plain text file."""
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
