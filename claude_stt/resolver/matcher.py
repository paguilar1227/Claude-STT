"""Fuzzy file matching — resolves parsed names to actual file paths."""

from __future__ import annotations

import os
from rapidfuzz import process, fuzz


class FileMatcher:
    """Matches file references against an indexed file list using multiple strategies."""

    def __init__(self, files: list[str]):
        self.files = files
        self.by_basename: dict[str, list[str]] = {}
        self.by_stem: dict[str, list[str]] = {}
        self.by_basename_lower: dict[str, list[str]] = {}
        self.by_stem_lower: dict[str, list[str]] = {}

        for filepath in files:
            basename = os.path.basename(filepath)
            stem = os.path.splitext(basename)[0]

            self.by_basename.setdefault(basename, []).append(filepath)
            self.by_stem.setdefault(stem, []).append(filepath)
            self.by_basename_lower.setdefault(basename.lower(), []).append(filepath)
            self.by_stem_lower.setdefault(stem.lower(), []).append(filepath)

    def match(self, raw_name: str, threshold: int = 65, limit: int = 5) -> list[dict]:
        """Resolve a parsed file reference to candidate paths.

        Args:
            raw_name: The parsed file name/reference from the parser.
            threshold: Minimum fuzzy match score (0-100).
            limit: Max number of candidates to return.

        Returns:
            List of match dicts sorted by score descending:
            [{"path": str, "score": int, "strategy": str}, ...]
        """
        if not raw_name:
            return []

        # Strategy 1: exact basename match
        if raw_name in self.by_basename:
            return [{"path": p, "score": 100, "strategy": "exact_basename"}
                    for p in self.by_basename[raw_name]]

        # Strategy 2: case-insensitive exact basename
        if raw_name.lower() in self.by_basename_lower:
            return [{"path": p, "score": 98, "strategy": "exact_basename_ci"}
                    for p in self.by_basename_lower[raw_name.lower()]]

        # Strategy 3: exact stem match (no extension spoken)
        if raw_name in self.by_stem:
            return [{"path": p, "score": 95, "strategy": "exact_stem"}
                    for p in self.by_stem[raw_name]]

        # Strategy 4: case-insensitive exact stem
        if raw_name.lower() in self.by_stem_lower:
            return [{"path": p, "score": 93, "strategy": "exact_stem_ci"}
                    for p in self.by_stem_lower[raw_name.lower()]]

        candidates = []

        # Strategy 5: fuzzy match against basenames
        basename_matches = process.extract(
            raw_name,
            list(self.by_basename.keys()),
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=threshold,
        )
        for match_name, score, _ in basename_matches:
            for path in self.by_basename[match_name]:
                candidates.append({
                    "path": path,
                    "score": int(score),
                    "strategy": "fuzzy_basename",
                })

        # Strategy 6: fuzzy match against stems (for when extension wasn't spoken)
        stem_matches = process.extract(
            raw_name,
            list(self.by_stem.keys()),
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=threshold,
        )
        for match_name, score, _ in stem_matches:
            for path in self.by_stem[match_name]:
                candidates.append({
                    "path": path,
                    "score": int(score),
                    "strategy": "fuzzy_stem",
                })

        # Strategy 7: if raw_name contains "/", match against full paths
        if "/" in raw_name:
            path_matches = process.extract(
                raw_name,
                self.files,
                scorer=fuzz.partial_ratio,
                limit=limit,
                score_cutoff=threshold,
            )
            for match_path, score, _ in path_matches:
                candidates.append({
                    "path": match_path,
                    "score": int(score),
                    "strategy": "fuzzy_path",
                })

        # Deduplicate and sort by score descending
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
            if c["path"] not in seen:
                seen.add(c["path"])
                unique.append(c)

        return unique[:limit]
