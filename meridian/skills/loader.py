from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from meridian.core.modes import Mode


@dataclass(frozen=True)
class SkillSection:
    name: str
    mode_alignment: List[Mode]
    content: str
    thinking_mode: Optional[str] = None


@dataclass(frozen=True)
class SkillFile:
    name: str
    description: str
    version: str
    sections: List[SkillSection]
    raw_content: str


_FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n", re.MULTILINE)
_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _parse_frontmatter(text: str) -> dict:
    m = _FRONTMATTER_RE.search(text)
    if not m:
        return {}
    block = m.group(1)
    data: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip().lower()] = v.strip()
    return data


def _mode_from_label(label: str) -> Optional[Mode]:
    s = label.strip().lower()
    # Common variants: "Mode 0 (EDA)", "Mode 0.5", "Mode 6.5"
    m = re.search(r"mode\s+([0-9]+(?:\.[0-9]+)?)", s)
    if not m:
        return None
    val = m.group(1)
    mapping = {
        "0.5": Mode.MODE_0_5,
        "0": Mode.MODE_0,
        "1": Mode.MODE_1,
        "2": Mode.MODE_2,
        "3": Mode.MODE_3,
        "4": Mode.MODE_4,
        "5": Mode.MODE_5,
        "6": Mode.MODE_6,
        "6.5": Mode.MODE_6_5,
        "7": Mode.MODE_7,
    }
    return mapping.get(val)


def _extract_mode_alignment_table(text: str) -> dict[str, List[Mode]]:
    """
    Parse a markdown table that contains 'MERIDIAN Mode Alignment'.

    We look for rows like:
    | Mode 0 (EDA) | ... | Section A, Section B |

    and return: { "Section A": [Mode.MODE_0], ... }
    """
    if "MERIDIAN Mode Alignment" not in text:
        return {}

    lines = text.splitlines()
    # Find the table start after the marker
    start = None
    for i, line in enumerate(lines):
        if "MERIDIAN Mode Alignment" in line:
            start = i
            break
    if start is None:
        return {}

    # Collect subsequent table lines beginning with '|'
    table_lines: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("|"):
            table_lines.append(line)
        elif table_lines:
            break

    if len(table_lines) < 2:
        return {}

    header = [c.strip().lower() for c in table_lines[0].strip("|").split("|")]
    # Find columns by name
    try:
        mode_col = header.index("mode")
    except ValueError:
        mode_col = 0
    primary_col = None
    for col_name in ("primary sections", "sections", "primary"):
        if col_name in header:
            primary_col = header.index(col_name)
            break
    if primary_col is None:
        # fall back to last column
        primary_col = len(header) - 1

    mapping: dict[str, List[Mode]] = {}
    for row in table_lines[2:]:  # skip header + separator
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) <= max(mode_col, primary_col):
            continue
        mode = _mode_from_label(cells[mode_col])
        if not mode:
            continue
        sections_cell = cells[primary_col]
        for section_name in re.split(r",\s*|\s*/\s*", sections_cell):
            section_name = section_name.strip()
            if not section_name:
                continue
            mapping.setdefault(section_name, []).append(mode)
    return mapping


def _extract_thinking_mode(section_text: str) -> Optional[str]:
    # Example: "⬜ EVIDENCE", "🔵 PROCESS"
    for line in section_text.splitlines()[:8]:
        line = line.strip()
        if re.match(r"^[^\w\s]\s+[A-Z_]+", line):
            return line
    return None


class SkillLoader:
    def __init__(self, skills_dir: Path = Path.home() / ".meridian-global" / "skills"):
        self.skills_dir = skills_dir

    def list_skills(self) -> List[str]:
        if not self.skills_dir.exists():
            return []
        return sorted([p.stem for p in self.skills_dir.glob("*.md") if p.is_file()])

    def load_skill(self, name: str) -> SkillFile:
        path = self.skills_dir / f"{name}.md"
        raw = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(raw)
        title = fm.get("name", name)
        description = fm.get("description", "")
        version = fm.get("version", "")

        alignment = _extract_mode_alignment_table(raw)

        # Split by ## headers
        headers = list(_HEADER_RE.finditer(raw))
        sections: list[SkillSection] = []
        for idx, h in enumerate(headers):
            section_name = h.group(1).strip()
            start = h.end()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(raw)
            body = raw[start:end].strip("\n")
            modes = alignment.get(section_name, [])
            thinking = _extract_thinking_mode(body)
            sections.append(
                SkillSection(name=section_name, mode_alignment=modes, content=body.strip(), thinking_mode=thinking)
            )

        return SkillFile(name=title, description=description, version=version, sections=sections, raw_content=raw)

    def get_sections_for_mode(self, skill_name: str, mode: Mode) -> List[SkillSection]:
        skill = self.load_skill(skill_name)
        return [s for s in skill.sections if mode in s.mode_alignment]

    def format_context(self, skill_name: str, mode: Mode) -> str:
        sections = self.get_sections_for_mode(skill_name, mode)
        chunks: list[str] = []
        for s in sections:
            header = f"## {s.name}"
            if s.thinking_mode:
                header += f"\n{ s.thinking_mode }"
            chunks.append(f"{header}\n\n{s.content}".strip())
        return "\n\n".join(chunks).strip()

