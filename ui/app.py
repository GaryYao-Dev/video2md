"""
Gradio Frontend

Features:
- Upload videos and select media files to process
- Preview Markdown (.md) and TXT/SRT side by side
- Auto-refresh lists after upload and processing; minimal manual actions

To run locally (optional):
    python ui/app.py

Requires:
    pip install gradio>=4
"""
from __future__ import annotations
from video2md.agents.summarize_host import summarize_host
from video2md.agents.research_host import research_host
from video2md.agents.whisper_host import whisper_host

from pathlib import Path
import asyncio
import re
from typing import List, Tuple

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover - optional until UI is built
    gr = None  # Lazy import pattern to avoid hard dependency now

# Ensure src/ is on sys.path when running from source tree
import sys
from pathlib import Path as _Path
_SRC = _Path(__file__).resolve().parents[1] / "src"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))


# Import orchestrators — keep UI thin and delegate to these


INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")


def _list_media_in_input() -> List[str]:
    media_exts = {
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma",
    }
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return [
        str(p.relative_to(INPUT_DIR))
        for p in INPUT_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in media_exts
    ]


def _list_txt_whisper() -> List[str]:
    # Deprecated: unified layout nests TXT under output/<basename>/<basename>.txt
    items: List[str] = []
    if OUTPUT_DIR.exists():
        for sub in sorted(OUTPUT_DIR.iterdir()):
            if sub.is_dir():
                for p in sub.glob("*.txt"):
                    if p.is_file():
                        items.append(str(p.relative_to(OUTPUT_DIR)))
    return items


def _list_md_output() -> List[str]:
    if not OUTPUT_DIR.exists():
        return []
    items: List[str] = []
    for sub in sorted(OUTPUT_DIR.iterdir()):
        if sub.is_dir():
            for p in sub.glob("*.md"):
                if p.is_file():
                    items.append(str(p.relative_to(OUTPUT_DIR)))
    return items


def _list_basenames() -> List[str]:
    """List basenames using per-media folders under output/.

    We consider a folder under output/ to be a candidate if it contains
    any of: <name>.md, <name>.txt, or <name>.srt.
    """
    names = set()
    if OUTPUT_DIR.exists():
        for sub in OUTPUT_DIR.iterdir():
            if not sub.is_dir():
                continue
            name = sub.name
            if (sub / f"{name}.md").exists() or (sub / f"{name}.txt").exists() or (sub / f"{name}.srt").exists():
                names.add(name)
    return sorted(names)


def _is_video_file(name: str) -> bool:
    video_exts = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}
    return Path(name).suffix.lower() in video_exts


async def process_selected(selected_rel_paths: List[str]) -> List[str]:
    """Run the end-to-end pipeline only for selected input files.

    selected_rel_paths: file paths relative to ./input
    Returns list of generated markdown summary paths.
    """
    # Run whisper only for the selected list
    srts = await whisper_host(input_dir=str(INPUT_DIR), selected_files=selected_rel_paths)
    if not srts:
        return []
    research = await research_host(srts)
    summaries = await summarize_host(srts, research)
    return summaries


def main():  # pragma: no cover - placeholder only
    if gr is None:
        print("Gradio is not installed yet. Install with: pip install gradio>=4")
        return

    with gr.Blocks(title="Video2MD", theme=gr.themes.Soft(primary_hue=gr.themes.colors.orange)) as demo:
        gr.Markdown("# Video2MD")
        gr.Markdown("""
        ### Convert videos to Markdown summaries with transcription and research.
        """)

        with gr.Row():
            # Left column: upload + input selection + action button + logs
            with gr.Column(scale=1, min_width=280):
                upload_files = gr.File(
                    label="Upload videos", file_count="multiple")
                upload_status = gr.Markdown(visible=True)

                input_files = gr.CheckboxGroup(
                    choices=_list_media_in_input(),
                    label="Select media files to process",
                )

                run_btn = gr.Button("Go")

                log_output = gr.Textbox(
                    lines=18, label="Logs", interactive=False)

            # Center column: Markdown/TXT/SRT selection + preview (tabbed)
            with gr.Column(scale=2):
                gr.Markdown("### Preview")
                base_list = gr.Dropdown(
                    choices=_list_basenames(), label="Select filename")
                # Responsive player style (limit height, fit width)
                gr.HTML("""
                <style>
                /* Global font family only; keep Gradio default borders/shadows */
                .gradio-container, .gradio-container * { font-family: Arial, sans-serif !important; }
                /* Ensure code editors are scrollable */
                .gradio-container .cm-editor { height: 40vh !important; }
                .gradio-container .cm-editor .cm-scroller { overflow: auto !important; }
                #md_player video{width:100%;max-width:100%;height:auto;max-height:60vh}
                </style>
                """)
                # Show media player above markdown so the video position is fixed at top
                md_video = gr.Video(
                    label="Media Player", interactive=False, elem_id="md_player")
                with gr.Tabs():
                    with gr.Tab("Markdown"):
                        md_preview = gr.Markdown(
                            "Select a filename above to preview Markdown.")
                    with gr.Tab("TXT"):
                        txt_code = gr.Code(
                            language=None, label="TXT Preview", interactive=False, lines=18
                        )
                    with gr.Tab("SRT"):
                        srt_code = gr.Code(
                            language=None, label="SRT Preview", interactive=False, lines=18
                        )

        # ----- Callbacks -----
    # Manual refresh buttons removed; use event-driven updates and a timer

        # Upload handler: validate and move into input directory
        def _handle_upload(files) -> Tuple[str, List[str]]:
            if not files:
                return ("No file selected.", gr.update())
            INPUT_DIR.mkdir(parents=True, exist_ok=True)
            saved = []
            wrong = []
            # files could be a list of TemporaryFile objects or file paths
            for f in (files if isinstance(files, list) else [files]):
                path = Path(getattr(f, "name", f))
                if not _is_video_file(path.name):
                    wrong.append(path.name)
                    continue
                dest = INPUT_DIR / path.name
                try:
                    # Some backends pass a path; others provide file-like with .read()
                    if hasattr(f, "read"):
                        dest.write_bytes(f.read())
                    else:
                        dest.write_bytes(Path(f).read_bytes())
                    saved.append(dest.name)
                except Exception as e:
                    wrong.append(f"{path.name} (save failed: {e})")

            status = "\n".join([
                f"✅ Saved: {', '.join(saved)}" if saved else "",
                f"⚠️ Not video or failed: {', '.join(wrong)}" if wrong else "",
            ]).strip() or "No files saved."
            # Also return updated input list
            return status, gr.update(choices=_list_media_in_input())

    # For browser compatibility: listen to change (and upload if available) so list refreshes immediately after upload
        upload_files.change(_handle_upload, inputs=upload_files, outputs=[
                            upload_status, input_files])
        if hasattr(upload_files, "upload"):
            upload_files.upload(_handle_upload, inputs=upload_files, outputs=[
                                upload_status, input_files])

    # Unified preview by basename: load MD/TXT/SRT together
        def _read_text_file(p: Path) -> str:
            if not p.exists():
                return ""
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                return p.read_text(errors="ignore")

    # Markdown preview handlers (list refresh occurs after summarization stage)

        def _extract_media_path_from_md(md_text: str, base_dir: Path) -> str | None:
            # Try HTML <video src="./media/xxx">
            m = re.search(
                r'<video[^>]*src=["\']([^"\']+)["\']', md_text, flags=re.IGNORECASE)
            candidate = m.group(1) if m else None
            if not candidate:
                # Try HTML <source src="./media/xxx">
                m_src = re.search(
                    r'<source[^>]*src=["\']([^"\']+)["\']', md_text, flags=re.IGNORECASE)
                candidate = m_src.group(1) if m_src else None
            if not candidate:
                # Try Markdown link: (./media/xxx)
                m2 = re.search(r"\(\./([^\)]+)\)", md_text)
                candidate = f"./{m2.group(1)}" if m2 else None
            if not candidate:
                return None
            # Normalize to absolute path under OUTPUT_DIR
            rel = candidate.replace("\\", "/")
            rel = rel[2:] if rel.startswith("./") else rel
            abs_path = base_dir / rel
            return str(abs_path) if abs_path.exists() else None

        def _sanitize_md_for_display(md_text: str) -> str:
            # Always remove inline <video> to avoid broken players occupying space
            # Remove including inner <source> content
            cleaned = re.sub(
                r"<video[\s\S]*?</video>", "\n> [Video preview is shown in the player above]\n", md_text, flags=re.IGNORECASE)
            return cleaned

        def _load_all_previews(basename: str):
            # Markdown
            if basename:
                base_dir = OUTPUT_DIR / basename
                md_path = base_dir / f"{basename}.md"
                md_text = _read_text_file(md_path)
                md_display = _sanitize_md_for_display(
                    md_text) if md_text else "(No Markdown content)"
                media_path = _extract_media_path_from_md(
                    md_text, base_dir) if md_text else None
                # TXT
                txt_path = base_dir / f"{basename}.txt"
                txt_text = _read_text_file(txt_path) or "(No TXT content)"
                # SRT
                srt_path = base_dir / f"{basename}.srt"
                srt_text = _read_text_file(srt_path) or "(No SRT content)"
            else:
                md_display, media_path, txt_text, srt_text = "", None, "", ""
            return (
                gr.update(value=md_display),
                gr.update(value=media_path),
                gr.update(value=txt_text),
                gr.update(value=srt_text),
            )

        base_list.change(_load_all_previews, inputs=base_list,
                         outputs=[md_preview, md_video, txt_code, srt_code])

        # Run pipeline for selected inputs only
        async def on_run(selected: List[str]):
            log = ""

            def step(msg: str):
                nonlocal log
                log += msg + "\n"
                return log

            if not selected:
                # No selection: return log only, without changing other components
                yield step("No input files selected."), gr.update(), gr.update()
                return

            # Initial message
            yield step(f"Start processing {len(selected)} file(s): {', '.join(selected)}"), gr.update(), gr.update()
            try:
                yield step("Running transcription (whisper)..."), gr.update(), gr.update()
                srts = await whisper_host(input_dir=str(INPUT_DIR), selected_files=selected)
                # After transcription: refresh basename list; most media are moved -> refresh input list and clear selections
                yield step(f"Transcription done: {len(srts)} SRT"), gr.update(choices=_list_basenames()), gr.update(choices=_list_media_in_input(), value=[])

                if not srts:
                    yield step("No SRTs produced; stopping."), gr.update(), gr.update()
                    return

                # New per-file flow: for each SRT, run Researcher -> Summarizer sequentially, but
                # process multiple files concurrently.
                yield step("Starting per-file pipelines (research -> summarize)..."), gr.update(), gr.update()

                # Limit concurrency to avoid spawning too many MCP servers at once
                # max_parallel = min(3, max(1, len(srts)))
                max_parallel = 2
                sem = asyncio.Semaphore(max_parallel)

                async def process_one(srt_path: str) -> tuple[str, str | None]:
                    fname = Path(srt_path).stem
                    async with sem:
                        # Research for a single file
                        try:
                            research_res = await research_host([srt_path])
                            # Summarize for the same single file
                            md_paths = await summarize_host([srt_path], research_res)
                            md_path = md_paths[0] if md_paths else None
                            return fname, md_path
                        except Exception as e:
                            return fname, None

                # Launch all tasks
                tasks = [asyncio.create_task(process_one(s)) for s in srts]

                completed = 0
                summaries_created: list[str] = []
                for coro in asyncio.as_completed(tasks):
                    fname, md_path = await coro
                    completed += 1
                    if md_path:
                        summaries_created.append(md_path)
                        msg = f"[{completed}/{len(srts)}] Done: {fname} -> {md_path}"
                    else:
                        msg = f"[{completed}/{len(srts)}] Failed: {fname} (see logs)"

                    # Incremental UI refresh so user can preview as items finish
                    yield step(msg), gr.update(choices=_list_basenames()), gr.update(choices=_list_media_in_input(), value=[])

                # Final summary
                if summaries_created:
                    yield (
                        step("All summarizations completed."),
                        gr.update(choices=_list_basenames()),
                        gr.update(choices=_list_media_in_input(), value=[]),
                    )
                else:
                    yield (
                        step(
                            "Summarization stage completed, but no Markdown files were generated."),
                        gr.update(choices=_list_basenames()),
                        gr.update(choices=_list_media_in_input(), value=[]),
                    )
            except Exception as e:
                # On error: sync input and basename lists to avoid stale selections
                yield step(f"Error occurred: {e}"), gr.update(choices=_list_basenames()), gr.update(choices=_list_media_in_input(), value=[])

        # Note: on_run now returns three outputs: logs, basename dropdown, and input file checkbox group
        run_btn.click(on_run, inputs=[input_files],
                      outputs=[log_output, base_list, input_files])

        # Timer: background refresh for input list to reduce manual refresh actions
        def _auto_refresh_inputs():
            return gr.update(choices=_list_media_in_input())

        try:
            timer = gr.Timer(3.0, active=True)
            timer.tick(_auto_refresh_inputs, outputs=input_files)
        except Exception:
            # Older Gradio versions may not have Timer; ignore if unavailable
            pass

    demo.launch()


if __name__ == "__main__":  # pragma: no cover - manual run only
    main()
