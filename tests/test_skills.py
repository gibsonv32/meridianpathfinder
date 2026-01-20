from __future__ import annotations

from pathlib import Path

from meridian.core.modes import Mode
from meridian.skills.loader import SkillLoader


def _write_skill(path: Path) -> None:
    path.write_text(
        """---
name: ML_SKILL
description: Testing skill file
version: 2.3.1
---

## MERIDIAN Mode Alignment

| Mode | Primary Sections |
|------|------------------|
| Mode 0 (EDA) | EDA Basics |
| Mode 2 (Feasibility) | Feasibility Checklist |

## EDA Basics
⬜ EVIDENCE

Do EDA.

## Feasibility Checklist
🔵 PROCESS

Do feasibility checks.
""",
        encoding="utf-8",
    )


def test_load_ml_skill(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_skill(skills_dir / "ML_SKILL.md")

    loader = SkillLoader(skills_dir=skills_dir)
    skill = loader.load_skill("ML_SKILL")
    assert skill.name == "ML_SKILL"
    assert skill.version == "2.3.1"
    assert any(s.name == "EDA Basics" for s in skill.sections)


def test_extract_mode_alignment(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_skill(skills_dir / "ML_SKILL.md")

    loader = SkillLoader(skills_dir=skills_dir)
    s0 = loader.get_sections_for_mode("ML_SKILL", Mode.MODE_0)
    s2 = loader.get_sections_for_mode("ML_SKILL", Mode.MODE_2)
    assert [s.name for s in s0] == ["EDA Basics"]
    assert [s.name for s in s2] == ["Feasibility Checklist"]


def test_format_context_includes_relevant_sections(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _write_skill(skills_dir / "ML_SKILL.md")

    loader = SkillLoader(skills_dir=skills_dir)
    ctx = loader.format_context("ML_SKILL", Mode.MODE_2)
    assert "## Feasibility Checklist" in ctx
    assert "Do feasibility checks." in ctx
    assert "## EDA Basics" not in ctx

