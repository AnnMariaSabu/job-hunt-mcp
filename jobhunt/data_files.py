"""Load my YAML data files: master resume, bullets, rubric.

The real files are PRIVATE (git-ignored). If a real file is missing, we use the
matching *.example.yaml file (fake data), so the project still runs for anyone.
"""

from pathlib import Path

import yaml

import config
from jobhunt import skills


def example_path(path: Path) -> Path:
    """data/master_resume.yaml -> data/master_resume.example.yaml"""
    return config.DATA_DIR / f"{path.stem}.example.yaml"


def resolve(path: Path) -> Path:
    """The real file if it exists, else the example file."""
    if path.exists():
        return path
    example = example_path(path)
    if example.exists():
        return example
    raise FileNotFoundError(f"Missing {path.name} (and no {example.name} either).")


def using_example(path: Path) -> bool:
    """True if we are using fake example data instead of my real file."""
    return not path.exists()


def load_yaml(path: Path) -> dict:
    # safe_load only reads plain data. (yaml.load could run code hidden in a file.)
    with open(resolve(path), encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_resume() -> dict:
    return load_yaml(config.MASTER_RESUME_PATH)


def check_bullets(bullets: list[dict], resume_skills: list[str]) -> list[str]:
    """SAFETY CHECK: find mistakes in the bullets file. Empty list = all good.

    Every skill tagged on a bullet must also be on my resume. Why? If a bullet
    says skills: [Docker] but my resume has no Docker, a tailored resume could
    claim a skill I never said I have. That is how resumes start to lie.
    """
    mine = {skills.canonical(s) for s in resume_skills}
    problems, seen = [], set()
    for number, bullet in enumerate(bullets, start=1):
        name = bullet.get("id") or f"bullet #{number}"
        if not bullet.get("id"):
            problems.append(f"{name}: missing id")
        elif name in seen:
            problems.append(f"{name}: id used twice")
        seen.add(name)
        if not str(bullet.get("text") or "").strip():
            problems.append(f"{name}: missing text")
        tags = bullet.get("skills") or []
        if not isinstance(tags, list):
            problems.append(f"{name}: skills must be a list, like [Python, SQL]")
            tags = []
        for skill in tags:
            if skills.canonical(skill) not in mine:
                problems.append(f"{name}: skill '{skill}' is not in master_resume.yaml")
    return problems


def load_bullets() -> list[dict]:
    """My bullets, but only after they pass the safety check."""
    bullets = load_yaml(config.MASTER_BULLETS_PATH).get("bullets", [])
    problems = check_bullets(bullets, load_resume().get("skills", []))
    if problems:
        raise ValueError("Fix master_bullets.yaml: " + "; ".join(problems))
    return bullets


def load_rubric() -> dict:
    return load_yaml(config.RUBRIC_PATH)


def example_warning() -> str | None:
    """A reminder when fake example data is being used."""
    fake = [p.name for p in (config.MASTER_RESUME_PATH, config.MASTER_BULLETS_PATH)
            if using_example(p)]
    if fake:
        return (f"Using EXAMPLE (fake) data because {', '.join(fake)} is missing. "
                "Copy the .example.yaml files and fill in your real details.")
    return None
