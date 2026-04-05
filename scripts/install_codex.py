#!/usr/bin/env python3
"""Install Agency agents into Codex as global `agency-*` skills."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_SOURCE_REPO = "https://github.com/liuhaoxh/agency-agents.git"
DEFAULT_UPSTREAM_REPO = "https://github.com/msitarzewski/agency-agents.git"
AGENT_ROOTS = [
    "academic",
    "design",
    "engineering",
    "game-development",
    "marketing",
    "paid-media",
    "product",
    "project-management",
    "sales",
    "spatial-computing",
    "specialized",
    "strategy",
    "support",
    "testing",
]
MANAGED_PREFIX = "agency-"


@dataclass
class AgentRecord:
    title: str
    description: str
    relative_path: str
    slug: str
    body: str


def run(cmd: list[str], *, cwd: Path | None = None, capture: bool = False) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return (result.stdout or "").strip()


def maybe_git_output(cmd: list[str], *, cwd: Path) -> str | None:
    try:
        output = run(cmd, cwd=cwd, capture=True)
    except subprocess.CalledProcessError:
        return None
    return output or None


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "skill"


def parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    if not raw_text.startswith("---\n"):
        return {}, raw_text.strip()

    parts = raw_text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, raw_text.strip()

    _, remainder = parts
    header = parts[0].splitlines()[1:]
    meta: dict[str, str] = {}
    for line in header:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, remainder.strip()


def collect_agent_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root in AGENT_ROOTS:
        root_path = repo_root / root
        if not root_path.exists():
            continue
        for path in sorted(root_path.rglob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            files.append(path)
    return files


def build_slug(path: Path, used: set[str], repo_root: Path) -> str:
    relative = path.relative_to(repo_root)
    stem_slug = slugify(path.stem)
    candidate = f"{MANAGED_PREFIX}{stem_slug}"
    if candidate not in used:
        used.add(candidate)
        return candidate

    parents = [slugify(part) for part in relative.parts[:-1]][::-1]
    for i in range(1, len(parents) + 1):
        prefix = "-".join(parents[:i])
        candidate = f"{MANAGED_PREFIX}{prefix}-{stem_slug}"
        if candidate not in used:
            used.add(candidate)
            return candidate

    index = 2
    while True:
        candidate = f"{MANAGED_PREFIX}{stem_slug}-{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def to_skill_description(title: str, original_description: str) -> str:
    original_description = re.sub(r"\s+", " ", original_description).strip()
    if not original_description:
        return f'Use when you explicitly want the imported Agency agent "{title}".'
    if original_description.lower().startswith("use when"):
        return original_description
    if original_description.endswith("."):
        original_description = original_description[:-1]
    return (
        f'Use when you explicitly want the imported Agency agent "{title}" for '
        f"{original_description}."
    )


def build_records(repo_root: Path) -> list[AgentRecord]:
    used: set[str] = set()
    records: list[AgentRecord] = []
    for path in collect_agent_files(repo_root):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        title = meta.get("name", path.stem.replace("-", " ").title())
        description = meta.get("description", "")
        slug = build_slug(path, used, repo_root)
        records.append(
            AgentRecord(
                title=title,
                description=description,
                relative_path=str(path.relative_to(repo_root)),
                slug=slug,
                body=body,
            )
        )
    return records


def render_skill(
    record: AgentRecord,
    *,
    source_repo_url: str,
    upstream_repo_url: str,
    commit: str,
) -> str:
    description = to_skill_description(record.title, record.description)
    body = record.body.strip()
    if body:
        body = f"{body}\n"
    return f"""---
name: {record.slug}
description: {description}
license: Imported from MIT-licensed Agency fork
source_repo: {source_repo_url}
upstream_repo: {upstream_repo_url}
source_commit: {commit}
source_path: {record.relative_path}
---

# {record.title}

Imported from the Agency fork for global Codex use.

## Source

- Source repo: {source_repo_url}
- Upstream repo: {upstream_repo_url}
- Pinned commit: `{commit}`
- Source file: `{record.relative_path}`

## Usage Note

This is a globally imported Agency skill for Codex. Prefer more specific project-local skills when they exist, and use this imported skill when you intentionally want the Agency persona/workflow.

## Original Metadata

- Original name: `{record.title}`
- Original description: {record.description or "(none supplied upstream)"}

## Imported Definition

{body}"""


def recreate_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_wrappers(
    records: Iterable[AgentRecord],
    *,
    wrapper_root: Path,
    source_repo_url: str,
    upstream_repo_url: str,
    commit: str,
) -> None:
    recreate_dir(wrapper_root)
    index_lines = [
        "# Agency Agents Codex Import",
        "",
        f"- Source repo: {source_repo_url}",
        f"- Upstream repo: {upstream_repo_url}",
        f"- Pinned commit: `{commit}`",
        "",
        "## Imported Skills",
        "",
    ]

    for record in records:
        skill_dir = wrapper_root / record.slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            render_skill(
                record,
                source_repo_url=source_repo_url,
                upstream_repo_url=upstream_repo_url,
                commit=commit,
            ),
            encoding="utf-8",
        )
        index_lines.append(f"- `{record.slug}` -> `{record.relative_path}`")

    (wrapper_root / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")


def refresh_symlinks(records: Iterable[AgentRecord], *, wrapper_root: Path, live_root: Path) -> list[str]:
    live_root.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    desired = {record.slug: wrapper_root / record.slug for record in records}
    for existing in live_root.glob(f"{MANAGED_PREFIX}*"):
        if existing.is_symlink():
            existing.unlink()
        elif existing.is_dir() or existing.is_file():
            warnings.append(f"Skipped non-symlink managed path: {existing}")

    for slug, target in desired.items():
        link_path = live_root / slug
        if link_path.exists():
            if link_path.is_symlink():
                link_path.unlink()
            else:
                warnings.append(f"Skipped existing non-symlink path: {link_path}")
                continue
        link_path.symlink_to(target, target_is_directory=True)

    return warnings


def write_manifest(
    *,
    manifest_path: Path,
    source_repo_url: str,
    upstream_repo_url: str,
    commit: str,
    records: list[AgentRecord],
    warnings: list[str],
) -> None:
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repo_url": source_repo_url,
        "upstream_repo_url": upstream_repo_url,
        "commit": commit,
        "count": len(records),
        "skills": [
            {
                "slug": record.slug,
                "title": record.title,
                "relative_path": record.relative_path,
            }
            for record in records
        ],
        "warnings": warnings,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Agency repo root. Defaults to the parent of this script.",
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("CODEX_HOME") or str(Path.home() / ".codex"),
        help="Codex home directory. Defaults to $CODEX_HOME or ~/.codex",
    )
    parser.add_argument(
        "--source-repo-url",
        default=None,
        help="Override the source repo URL recorded in generated skills.",
    )
    parser.add_argument(
        "--upstream-repo-url",
        default=None,
        help="Override the upstream repo URL recorded in generated skills.",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Compatibility flag from the old wrapper. Ignored because this installer uses the current checkout.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).expanduser().resolve()
    codex_home = Path(args.codex_home).expanduser().resolve()
    wrapper_root = codex_home / "vendor_imports" / "skills" / "agency-agents"
    live_root = codex_home / "skills"
    manifest_path = codex_home / "vendor_imports" / "agency-agents-codex" / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    source_repo_url = (
        args.source_repo_url
        or maybe_git_output(["git", "remote", "get-url", "origin"], cwd=repo_root)
        or DEFAULT_SOURCE_REPO
    )
    upstream_repo_url = (
        args.upstream_repo_url
        or maybe_git_output(["git", "remote", "get-url", "upstream"], cwd=repo_root)
        or DEFAULT_UPSTREAM_REPO
    )
    commit = maybe_git_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root) or "unknown"

    records = build_records(repo_root)
    write_wrappers(
        records,
        wrapper_root=wrapper_root,
        source_repo_url=source_repo_url,
        upstream_repo_url=upstream_repo_url,
        commit=commit,
    )
    warnings = refresh_symlinks(records, wrapper_root=wrapper_root, live_root=live_root)
    write_manifest(
        manifest_path=manifest_path,
        source_repo_url=source_repo_url,
        upstream_repo_url=upstream_repo_url,
        commit=commit,
        records=records,
        warnings=warnings,
    )

    print(f"Installed {len(records)} Agency Codex skills from {commit}.")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
