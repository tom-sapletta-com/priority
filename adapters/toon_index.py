#!/usr/bin/env python3
"""Small deterministic reader for code2llm TOON map indexes.

The map format is intentionally consumed as an index, not as source code.  The
reader understands the stable sections used by the attached map.toon files:
header comments, ``M[n]:`` module rows and ``D:`` symbol details.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_HEADER_RE = re.compile(r"^#\s*(?P<organization>[^|]+?)\s*\|.*\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$")
_MODULE_START_RE = re.compile(r"^M\[(?P<count>\d+)\]:$")
_DETAIL_PATH_RE = re.compile(r"^  (?P<path>.+):$")
_SYMBOL_RE = re.compile(r"^    (?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P<rest>.*)$")
_METHOD_RE = re.compile(r"(?:^|,)\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")


@dataclass(frozen=True)
class ToonDetail:
    imports: tuple[str, ...]
    exports: tuple[str, ...]
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class ToonIndex:
    path: Path
    organization: str
    generated_date: str | None
    declared_module_count: int | None
    modules: dict[str, int]
    details: dict[str, ToonDetail]
    sha256: str

    def modules_under(self, prefix: str) -> list[str]:
        return sorted(path for path in self.modules if path.startswith(prefix))

    def has_module(self, path: str) -> bool:
        return path in self.modules

    def has_symbol(self, path: str, symbol: str) -> bool:
        detail = self.details.get(path)
        if detail is None:
            return False
        return symbol in detail.symbols or symbol in detail.exports

    def project_roots(self) -> dict[str, int]:
        roots: dict[str, int] = {}
        for module in self.modules:
            root = module.split("/", 1)[0] if "/" in module else "."
            roots[root] = roots.get(root, 0) + 1
        return dict(sorted(roots.items()))


def _split_names(raw: str) -> tuple[str, ...]:
    values: list[str] = []
    for item in raw.split(","):
        name = item.strip()
        if not name:
            continue
        # Export rows can include compact signatures such as foo(-1).  Keep the
        # exported identifier only; detailed symbol rows retain the same name.
        name = re.split(r"[(:]", name, maxsplit=1)[0].strip()
        if name and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            values.append(name)
    return tuple(dict.fromkeys(values))


def parse_toon_index(path: Path) -> ToonIndex:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    organization = "unknown"
    generated_date: str | None = None
    declared_module_count: int | None = None
    modules: dict[str, int] = {}
    detail_acc: dict[str, dict[str, list[str]]] = {}

    for line in lines[:12]:
        match = _HEADER_RE.match(line)
        if match:
            organization = match.group("organization").strip()
            generated_date = match.group("date")
            break

    section = "header"
    current_detail: str | None = None
    for line in lines:
        start = _MODULE_START_RE.match(line)
        if start:
            declared_module_count = int(start.group("count"))
            section = "modules"
            current_detail = None
            continue
        if line == "D:":
            section = "details"
            current_detail = None
            continue

        if section == "modules":
            if not line.startswith("  ") or "," not in line:
                continue
            path_part, count_part = line[2:].rsplit(",", 1)
            if count_part.isdigit():
                modules[path_part] = int(count_part)
            continue

        if section != "details":
            continue

        detail_match = _DETAIL_PATH_RE.match(line)
        if detail_match:
            current_detail = detail_match.group("path")
            detail_acc.setdefault(current_detail, {"imports": [], "exports": [], "symbols": []})
            continue
        if current_detail is None:
            continue
        stripped = line.strip()
        if stripped.startswith("i: "):
            detail_acc[current_detail]["imports"].extend(_split_names(stripped[3:]))
            continue
        if stripped.startswith("e: "):
            detail_acc[current_detail]["exports"].extend(_split_names(stripped[3:]))
            continue
        symbol_match = _SYMBOL_RE.match(line)
        if symbol_match:
            name = symbol_match.group("name")
            if name not in {"i", "e"}:
                detail_acc[current_detail]["symbols"].append(name)
            # code2llm compresses class/object members onto the same detail row,
            # e.g. ``ControlService: close(0),generate_repair_plan(4)``.
            # They are implementation evidence too, so retain the identifiers
            # instead of treating only the owning class as a symbol.
            rest = symbol_match.group("rest")
            if ":" in rest:
                member_list = rest.split(":", 1)[1]
                for member_match in _METHOD_RE.finditer(member_list):
                    detail_acc[current_detail]["symbols"].append(member_match.group("name"))

    details = {
        detail_path: ToonDetail(
            imports=tuple(dict.fromkeys(values["imports"])),
            exports=tuple(dict.fromkeys(values["exports"])),
            symbols=tuple(dict.fromkeys(values["symbols"])),
        )
        for detail_path, values in detail_acc.items()
    }
    return ToonIndex(
        path=path,
        organization=organization,
        generated_date=generated_date,
        declared_module_count=declared_module_count,
        modules=modules,
        details=details,
        sha256="sha256:" + hashlib.sha256(raw).hexdigest(),
    )


def diff_toon_indexes(before: ToonIndex, after: ToonIndex) -> dict[str, object]:
    before_modules = set(before.modules)
    after_modules = set(after.modules)
    added = sorted(after_modules - before_modules)
    removed = sorted(before_modules - after_modules)
    changed = sorted(
        path
        for path in before_modules & after_modules
        if before.modules[path] != after.modules[path]
    )

    def roots(paths: Iterable[str]) -> dict[str, int]:
        result: dict[str, int] = {}
        for path in paths:
            root = path.split("/", 1)[0] if "/" in path else "."
            result[root] = result.get(root, 0) + 1
        return dict(sorted(result.items(), key=lambda item: (-item[1], item[0])))

    return {
        "schema": "subactor.toon-map-diff/v1",
        "organization": after.organization,
        "before": {
            "path": str(before.path),
            "sha256": before.sha256,
            "generatedDate": before.generated_date,
            "moduleCount": len(before.modules),
        },
        "after": {
            "path": str(after.path),
            "sha256": after.sha256,
            "generatedDate": after.generated_date,
            "moduleCount": len(after.modules),
        },
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changedLineCount": len(changed),
        },
        "addedProjectRoots": roots(added),
        "removedProjectRoots": roots(removed),
        "addedModules": added,
        "removedModules": removed,
        "changedModules": changed,
    }
