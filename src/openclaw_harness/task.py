from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


REQUIRED_FIELDS = ("id", "name", "category", "prompt")


@dataclass(slots=True)
class TaskSpec:
    id: str
    name: str
    category: str
    prompt: str
    description: str = ""
    source_path: str = ""
    body: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def resolve_task_path(task_file: str, *, scenario_path: Path) -> Path:
    candidate = Path(task_file)
    if candidate.is_absolute():
        return candidate.resolve()
    return (scenario_path.parent / candidate).resolve()


def load_task(path: Path) -> TaskSpec:
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(raw)
    missing = [field for field in REQUIRED_FIELDS if not str(frontmatter.get(field, "")).strip()]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"task file {path} is missing required frontmatter fields: {joined}")
    return TaskSpec(
        id=str(frontmatter["id"]).strip(),
        name=str(frontmatter["name"]).strip(),
        category=str(frontmatter["category"]).strip(),
        prompt=str(frontmatter["prompt"]).strip(),
        description=str(frontmatter.get("description", "")).strip(),
        source_path=str(path.resolve()),
        body=body.strip(),
    )


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("task frontmatter must start with '---'")
    try:
        end_index = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("task frontmatter is missing the closing '---'") from exc

    frontmatter_lines = lines[1:end_index]
    body = "\n".join(lines[end_index + 1 :]).strip()
    payload: dict[str, str] = {}
    index = 0
    while index < len(frontmatter_lines):
        line = frontmatter_lines[index]
        stripped = line.strip()
        index += 1
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line!r}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value in {"|", ">"}:
            block_lines: list[str] = []
            while index < len(frontmatter_lines):
                candidate = frontmatter_lines[index]
                if candidate.startswith("  ") or candidate.startswith("\t"):
                    block_lines.append(candidate[2:] if candidate.startswith("  ") else candidate.lstrip("\t"))
                    index += 1
                    continue
                if not candidate.strip():
                    block_lines.append("")
                    index += 1
                    continue
                break
            if value == ">":
                payload[key] = " ".join(part.strip() for part in block_lines if part.strip()).strip()
            else:
                payload[key] = "\n".join(block_lines).rstrip()
            continue
        payload[key] = strip_quotes(value)
    return payload, body


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
