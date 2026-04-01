"""Pipeline orchestrator — parse, index, match.

Supports synchronous resolution and background indexing for
non-blocking integration with Claude-STT.
"""

from __future__ import annotations

import logging
import threading
import time

from .parser import parse
from .indexer import (
    build_index, load_index, save_index, save_cache, smart_load, find_repo_root,
)
from .matcher import FileMatcher

logger = logging.getLogger(__name__)


class VoiceFileResolver:
    """End-to-end voice-to-file-path resolution.

    Can be initialized synchronously (for CLI) or with background indexing
    (for Claude-STT integration where blocking startup is unacceptable).
    """

    def __init__(self, project_root: str, index_path: str | None = None):
        """Initialize the resolver synchronously.

        Args:
            project_root: Root directory of the codebase.
            index_path: Path to a plain-text file index. If None, uses
                       smart_load (external cache + git delta).
        """
        self.project_root = project_root
        self._matcher: FileMatcher | None = None
        self._ready = threading.Event()

        if index_path:
            try:
                files = load_index(index_path)
                logger.info(f"Loaded {len(files)} files from index at {index_path}")
            except FileNotFoundError:
                files = build_index(project_root)
                save_index(files, index_path)
        else:
            files, _ = smart_load(project_root)

        self._matcher = FileMatcher(files)
        self._ready.set()

    @classmethod
    def background(cls, project_root: str) -> VoiceFileResolver:
        """Create a resolver that indexes in the background.

        Returns immediately. The resolver is not ready until indexing
        completes. Use is_ready() to check, or just call resolve() —
        it returns gracefully if not ready yet.
        """
        instance = object.__new__(cls)
        instance.project_root = project_root
        instance._matcher = None
        instance._ready = threading.Event()

        thread = threading.Thread(
            target=instance._background_index,
            daemon=True,
        )
        thread.start()
        return instance

    def _background_index(self):
        """Run indexing in a background thread."""
        try:
            files, from_cache = smart_load(self.project_root)
            self._matcher = FileMatcher(files)
            self._ready.set()
            logger.info(
                f"File resolver ready: {len(files)} files indexed "
                f"({'from cache' if from_cache else 'full scan'})"
            )
        except Exception:
            logger.exception("Background indexing failed")
            self._ready.set()  # unblock callers even on failure

    def is_ready(self) -> bool:
        """Check if the resolver has finished indexing."""
        return self._ready.is_set()

    def resolve(self, spoken_text: str, threshold: int = 65, limit: int = 5) -> dict:
        """Resolve spoken text to a file path.

        If the resolver isn't ready yet (background indexing in progress),
        returns detected=False so the caller can fall back to raw text.
        """
        t0 = time.monotonic()

        # Not ready yet — graceful degradation
        if self._matcher is None:
            elapsed = (time.monotonic() - t0) * 1000
            return {
                "detected": False,
                "raw_name": "",
                "resolved_path": None,
                "score": None,
                "candidates": [],
                "latency_ms": round(elapsed, 1),
                "ready": False,
            }

        # Stage 1: Parse spoken text
        parsed = parse(spoken_text)

        if not parsed["detected"]:
            elapsed = (time.monotonic() - t0) * 1000
            return {
                "detected": False,
                "raw_name": "",
                "resolved_path": None,
                "score": None,
                "candidates": [],
                "latency_ms": round(elapsed, 1),
                "ready": True,
            }

        # Stage 2: Match against file index
        candidates = self._matcher.match(
            parsed["raw_name"], threshold=threshold, limit=limit
        )

        resolved_path = candidates[0]["path"] if candidates else None
        score = candidates[0]["score"] if candidates else None

        elapsed = (time.monotonic() - t0) * 1000

        return {
            "detected": True,
            "raw_name": parsed["raw_name"],
            "resolved_path": resolved_path,
            "score": score,
            "candidates": candidates,
            "latency_ms": round(elapsed, 1),
            "ready": True,
        }
