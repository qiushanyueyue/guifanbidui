#!/usr/bin/env python3
"""Validate the repository-level project memory contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_HEADINGS = {
    "AGENTS.md": ["# 仓库代理工作协议", "## 新对话启动：最多五步", "## 记忆更新协议", "## 完成定义"],
    "MEMORY.md": ["# 项目记忆索引", "## 当前关键事实", "## 不可忘记的风险", "## 更新规则"],
    "docs/PROJECT_CHARTER.md": ["# 项目纲领", "## 使命", "## 核心原则", "## 非目标", "## 完成定义"],
    "docs/project-memory/README.md": ["# 项目记忆使用说明", "## 分层结构", "## 更新判定", "## 隐私与保留"],
    "docs/project-memory/CURRENT.md": ["# 当前事实快照", "## 仓库与部署", "## 数据快照", "## 验证基线", "## 当前风险与未验证项"],
    "docs/project-memory/HISTORY.md": ["# 项目记忆历史", "## 追加模板"],
    "docs/project-memory/decisions/README.md": ["# 架构决策记录", "## 索引"],
    "docs/project-memory/decisions/ADR-0001-filesystem-layered-memory.md": ["# ADR-0001", "## 背景", "## 决定", "## 替代方案", "## 后果", "## 复核条件"],
}

MEMORY_FILES = tuple(REQUIRED_HEADINGS)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credentialed database url": re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):\/\/[^\s/:]+:[^\s/@]+@", re.IGNORECASE),
    "provider token": re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b"),
    "assigned secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\b\s*[:=]\s*[\"']?"
        r"(?!<|\$\{|hidden\b|redacted\b|none\b|未配置)([A-Za-z0-9_./+=-]{12,})"
    ),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def scan_for_secrets(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def validate_memory(root: Path) -> list[str]:
    errors: list[str] = []
    scanned_paths: set[Path] = set()
    for relative, headings in REQUIRED_HEADINGS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required file: {relative}")
            continue
        scanned_paths.add(path.resolve())
        text = _read(path)
        for heading in headings:
            if heading not in text:
                errors.append(f"missing heading in {relative}: {heading}")
        for secret_type in scan_for_secrets(text):
            errors.append(f"possible {secret_type} in {relative}")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0]
            if not target or re.match(r"^(?:https?://|mailto:)", target):
                continue
            if target.startswith("/"):
                errors.append(f"absolute local link in {relative}: {raw_target}")
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"broken local link in {relative}: {raw_target}")

    decisions_dir = root / "docs/project-memory/decisions"
    for path in sorted(decisions_dir.glob("ADR-*.md")):
        if path.resolve() in scanned_paths:
            continue
        relative = path.relative_to(root).as_posix()
        text = _read(path)
        for secret_type in scan_for_secrets(text):
            errors.append(f"possible {secret_type} in {relative}")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0]
            if not target or re.match(r"^(?:https?://|mailto:)", target):
                continue
            if target.startswith("/") or not (path.parent / target).resolve().exists():
                errors.append(f"broken local link in {relative}: {raw_target}")

    current = root / "docs/project-memory/CURRENT.md"
    if current.is_file():
        text = _read(current)
        for marker in ("as_of:", "verification:", "evidence_policy:"):
            if marker not in text:
                errors.append(f"CURRENT.md missing temporal evidence marker: {marker}")

    agents = root / "AGENTS.md"
    if agents.is_file():
        text = _read(agents)
        for required_reference in (
            "docs/PROJECT_CHARTER.md",
            "MEMORY.md",
            "docs/project-memory/CURRENT.md",
            "python scripts/check_project_memory.py",
        ):
            if required_reference not in text:
                errors.append(f"AGENTS.md missing startup/update reference: {required_reference}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_memory(args.root.resolve())
    if errors:
        print("project memory validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"project memory validation passed: {len(MEMORY_FILES)} required files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
