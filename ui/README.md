# Gradio UI (placeholder)

This directory will host a lightweight Gradio frontend for the pipeline:

- Upload or select media files
- Trigger transcription (via Whisper host agent)
- Review research findings
- Generate and preview Markdown summaries

Planned modules:

- `app.py` — entry point for the Gradio app
- `components/controls.py` — reusable UI controls (inputs, buttons, status)

Notes:

- Keep UI logic thin. Delegate work to functions in `video2md.agents.*`.
- Prefer async-friendly handlers (Gradio supports async functions).
- Avoid embedding long prompts in UI; rely on `video2md.prompt_loader` and files under `prompts/`.

Run (optional):

```bash
# From repo root
python3 ui/app.py
```

Behavior:

- The input file list auto-refreshes after uploads and after a run completes.
- A small background timer also refreshes the input list every ~3 seconds to pick up external file changes.
- After processing, moved media will be unselected automatically to prevent stale selections.

Dependencies (to be added later):

- gradio>=4
