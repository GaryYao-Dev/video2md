from pathlib import Path
from typing import Any, Dict, Optional
import importlib
import importlib.util


class PromptLoader:
    """Load and render prompt templates from the project's prompts/ directory.

    Conventions:
    - Prompts live in project_root/prompts/* (preferred) or src/prompts/*
      with extensions like .md, .j2, or .txt
    - Placeholders use double curly braces, e.g., {{NAME}}
    - If Jinja2 is available, full templating (loops/ifs/includes) is supported
    - Otherwise, a simple safe replacement is used (missing keys left as-is)
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # Determine candidate prompt directories relative to this module
        pkg_dir = Path(__file__).resolve().parent  # .../src/video2md

        def find_project_root(start: Path) -> Optional[Path]:
            for parent in [start] + list(start.parents):
                if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                    return parent
            return None

        candidates: list[Path] = []

        # 1) If base_dir provided, honor it (it can be the project root or the prompts dir)
        if base_dir is not None:
            base = Path(base_dir)
            candidates.append(base if base.name ==
                              "prompts" else base / "prompts")

        # 2) Try repo root discovered by markers
        root = find_project_root(pkg_dir)
        if root is not None:
            candidates.append(root / "prompts")

        # 3) Common fallbacks based on repo layout
        candidates.append(pkg_dir.parent.parent / "prompts")  # ../../prompts
        candidates.append(pkg_dir.parent / "prompts")  # ../prompts

        # De-duplicate while preserving order
        seen: set[Path] = set()
        ordered_candidates: list[Path] = []
        for p in candidates:
            if p not in seen:
                seen.add(p)
                ordered_candidates.append(p)

        self._prompt_dirs = ordered_candidates

        self._jinja_env = None
        # Lazy optional import for Jinja2 to avoid hard dependency at import time
        if importlib.util.find_spec("jinja2") is not None:
            jinja2 = importlib.import_module("jinja2")
            # Only include existing directories in the loader search path
            existing_dirs = [str(p) for p in self._prompt_dirs if p.exists()]
            loader = jinja2.FileSystemLoader(
                existing_dirs or [str(self._prompt_dirs[0])])
            self._jinja_env = jinja2.Environment(
                loader=loader,
                autoescape=jinja2.select_autoescape(
                    enabled_extensions=(".html", ".xml")),
                undefined=jinja2.StrictUndefined,
                trim_blocks=True,
                lstrip_blocks=True,
            )

    def _resolve_path(self, name: str) -> Path:
        # Try common extensions in order across all candidate directories
        tried: list[Path] = []
        for prompt_dir in self._prompt_dirs:
            for ext in (".md", ".j2", ".txt"):
                path = prompt_dir / f"{name}{ext}"
                tried.append(path)
                if path.exists():
                    return path
            # Fallback to exact name if it includes extension
            exact = prompt_dir / name
            tried.append(exact)
            if exact.exists():
                return exact

        # If nothing matched, show helpful error with all locations tried
        tried_str = "\n".join(str(p) for p in tried)
        raise FileNotFoundError(
            "Prompt not found. Searched the following paths (with .md/.j2/.txt and exact):\n"
            f"{tried_str}"
        )

    def load(self, name: str) -> str:
        path = self._resolve_path(name)
        return path.read_text(encoding="utf-8")

    def render(self, name: str, **kwargs: Any) -> str:
        # Prefer Jinja2 if available to support real templating
        if self._jinja_env is not None:
            template_name = self._resolve_path(name).name
            try:
                template = self._jinja_env.get_template(template_name)
                return template.render(**kwargs)
            except Exception:
                # Fallback to raw load on templating errors to avoid hard failures
                pass
        # Simple replacement fallback
        text = self.load(name)
        return self._replace_placeholders(text, kwargs)

    @staticmethod
    def _replace_placeholders(text: str, values: Dict[str, Any]) -> str:
        rendered = text
        for key, val in (values or {}).items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(val))
        return rendered


# Convenience singleton
default_loader = PromptLoader()
