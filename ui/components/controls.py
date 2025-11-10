"""
Placeholder for reusable Gradio controls.

Suggested components:
- Directory picker (text input with folder dialog)
- Progress/status area
- Result gallery (list of links to generated Markdown)

Keep functions pure and return Gradio components; avoid business logic here.
"""

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover - optional until UI is built
    gr = None


def directory_input(default: str = "input"):
    if gr is None:
        return None
    return gr.Textbox(value=default, label="Input directory")
