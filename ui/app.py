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
import sys
import os
# Ensure src is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from video2md.agents.summarize_host import summarize_host
from video2md.agents.research_host import research_host
from video2md.agents.whisper_host import whisper_host
from video2md.utils.dependency_checker import DependencyChecker
from agents import trace  # Import trace for creating unified workflow

from pathlib import Path
import asyncio
import json
import re
import shutil
import tempfile
from typing import List, Optional, Tuple

# Import downloaders for URL-based video downloading
try:
    from video2md.downloaders import (
        get_downloader,
        detect_platform,
        DownloadError,
        PlatformNotSupportedError,
        SUPPORTED_PLATFORMS,
    )
    from video2md.downloaders.base import Platform
    DOWNLOADERS_AVAILABLE = True
except ImportError:
    DOWNLOADERS_AVAILABLE = False

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


async def process_selected(selected_rel_paths: List[str], transcribe_method: str = "local", prompt_variant: str = "github_project", user_notes: str = "") -> List[str]:
    """Run the end-to-end pipeline only for selected input files.

    selected_rel_paths: file paths relative to ./input
    transcribe_method: 'local' for faster-whisper or 'openai' for OpenAI API
    Returns list of generated markdown summary paths.
    """
    # Run whisper only for the selected list
    srts = await whisper_host(input_dir=str(INPUT_DIR), selected_files=selected_rel_paths, transcribe_method=transcribe_method)
    if not srts:
        return []
    research = await research_host(srts, prompt_variant=prompt_variant, user_notes=user_notes)
    summaries = await summarize_host(srts, research)
    return summaries


async def download_video_task(
    url: str,
    topic_name: str = "",
    progress_callback: Optional[callable] = None,
) -> Tuple[Optional[str], str]:
    """
    Download video from URL to input directory.
    
    Args:
        url: Video URL to download
        topic_name: User-provided topic name for the video (required)
        progress_callback: Optional callback for progress updates
    
    Returns:
        Tuple of (video_path, status_message)
    """
    if not DOWNLOADERS_AVAILABLE:
        return None, "❌ URL downloaders not available. Please check dependencies."
    
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    url = url.strip()
    if not url:
        return None, "❌ Please enter a video URL."
    
    # Validate topic name
    topic_name = topic_name.strip()
    if not topic_name:
        return None, "❌ Please enter a topic name for the video"
    
    # Sanitize topic name for use as directory/file name
    import re
    safe_topic_name = re.sub(r'[<>:"/\\|?*]', '_', topic_name)
    safe_topic_name = safe_topic_name[:100]  # Limit length
    
    # Detect platform
    platform = detect_platform(url)
    if platform is None:
        return None, f"❌ Unsupported platform. Supported: {', '.join(p.value for p in SUPPORTED_PLATFORMS.keys())}"
    
    platform_name = SUPPORTED_PLATFORMS.get(platform, platform.value)
    log(f"🔍 Detected platform: {platform_name}")
    log(f"📁 Topic: {topic_name}")
    
    try:
        # Get downloader
        downloader = get_downloader(url)
        
        # Create output directory for metadata (video will go to input)
        # We create the output folder now to store metadata, but the video 
        # will be processed from input/ and moved here later by the pipeline.
        final_output_dir = OUTPUT_DIR / safe_topic_name
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download video to a temporary location or directly to input?
        # Let's download to input directly to avoid copy overhead
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # We use a temp dir for download to ensure we can rename strictly
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Download video
            log(f"⬇️ Downloading video from {platform_name}...")
            
            # Progress hook for downloader
            def download_progress_hook(d):
                if d.get('status') == 'downloading':
                    # Helper to strip ANSI codes
                    def strip_ansi(s):
                        return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)

                    percent_str = strip_ansi(d.get('_percent_str', '')).strip()
                    speed_str = strip_ansi(d.get('_speed_str', '')).strip()
                    eta_str = strip_ansi(d.get('_eta_str', '')).strip()
                    
                    if percent_str and '%' in percent_str:
                        try:
                            # Extract numeric value
                            p_val = float(percent_str.replace('%', ''))
                            
                            # Check if we should log (0, 33, 66, 100)
                            should_log = False
                            
                            # Log 0% only once (approx)
                            if 0.0 <= p_val < 0.1: should_log = True
                            # Log ~33%
                            elif 33.0 <= p_val <= 34.0: should_log = True
                            # Log ~66%
                            elif 66.0 <= p_val <= 67.0: should_log = True
                            # Log 100%
                            elif p_val >= 99.9: should_log = True
                            
                            # Prevent spamming: simple state tracking would be better but 
                            # given the stateless hook, strict ranges help.
                            # The previous logic allowed < 1.0 which caused 0.1, 0.3 etc.
                            
                            if should_log:
                                log(f"⬇️ Downloading: {percent_str} (Speed: {speed_str}, ETA: {eta_str})")
                        except ValueError:
                            pass
            
            result = await downloader.download(url, temp_path, progress_hook=download_progress_hook)
            
            video_path = result.file_path
            video_ext = video_path.suffix or ".mp4"
            
            # Target path in input directory
            input_video_path = INPUT_DIR / f"{safe_topic_name}{video_ext}"
            
            # Move downloaded file to input directory
            shutil.move(str(video_path), str(input_video_path))
            
            log(f"✅ Downloaded to input: {input_video_path.name}")
            
            # Save metadata to output directory
            metadata_path = final_output_dir / f"{safe_topic_name}.json"
            metadata = {
                "topic": topic_name,
                "title": result.title,
                "video_id": result.video_id,
                "platform": result.platform.value,
                "duration": result.duration,
                "cover_url": result.cover_url,
                "source_url": url,
                **result.raw_info,
            }
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return str(input_video_path), f"✅ Ready to process: {safe_topic_name}"

    except PlatformNotSupportedError as e:
        return None, f"❌ Platform not supported: {e}"
    except DownloadError as e:
        return None, f"❌ Download failed: {e}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"❌ Error: {e}"


def main():  # pragma: no cover - placeholder only
    # Check dependencies before starting UI
    print("Checking dependencies...")
    DependencyChecker.validate_or_exit(require_ffmpeg=True, require_node=True)
    
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
                # Tabbed input mode selection
                with gr.Tabs() as input_tabs:
                    # Tab 1: File Upload (existing functionality)
                    with gr.TabItem("📁 Local Files", id="file_tab"):
                        upload_files = gr.File(
                            label="Upload videos", file_count="multiple")
                        upload_status = gr.Markdown(visible=True)
                    
                    # Tab 2: URL Download (new functionality)
                    # Tab 2: URL Download (new functionality)
                    with gr.TabItem("🔗 Video URL", id="url_tab"):
                        gr.Markdown("""
                        **Supported Platforms**: Bilibili, YouTube
                        """)
                        topic_input = gr.Textbox(
                            label="📌 Topic Name *Required*",
                            placeholder="e.g., Python_Tutorial, Product_Demo...",
                            lines=1,
                        )
                        url_input = gr.Textbox(
                            label="🔗 Video URL",
                            placeholder="https://www.bilibili.com/video/BVxxxxx or https://youtu.be/xxxxx",
                            lines=2,
                        )
                        detected_platform = gr.Markdown(value="", visible=False)
                        url_run_btn = gr.Button("Download to Input", variant="primary")
                        url_log_output = gr.Textbox(label="Download Logs", lines=5, max_lines=10, interactive=False)

                # Shared settings and processing
                gr.Markdown("---")
                
                input_files = gr.CheckboxGroup(
                    choices=_list_media_in_input(),
                    label="Select media files to process (from Uploads or Downloads)",
                )
                
                with gr.Row():
                    transcribe_method = gr.Radio(
                        choices=[
                            ("Local Whisper (faster-whisper)", "local"),
                            ("OpenAI Whisper API (whisper-1)", "openai"),
                        ],
                        value="openai",
                        label="Transcription Method",
                    )

                    prompt_select = gr.Dropdown(
                        choices=[
                            "github_project",
                            "general",
                            "tutorial",
                            "review_analysis",
                        ],
                        value="github_project",
                        label="Research prompt",
                        allow_custom_value=False,
                    )

                user_notes = gr.Textbox(
                    lines=4,
                    label="User notes (optional)",
                    info="Add author comments, product model numbers, repo URLs, or any hints to bias research.",
                )
                
                run_btn = gr.Button("Go", variant="primary")
                
                log_output = gr.Textbox(
                    lines=18, label="Logs", interactive=False)

            # Center column: Markdown/TXT/SRT selection + preview (tabbed)
            with gr.Column(scale=2):
                gr.Markdown("### Preview")
                # Get initial basenames and set default value to first item if available
                initial_basenames = _list_basenames()
                initial_value = initial_basenames[0] if initial_basenames else None
                # Select filename, Download folder and trace link in the same row
                with gr.Row():
                    base_list = gr.Dropdown(
                        choices=initial_basenames, 
                        value=initial_value,
                        label="Select filename",
                        scale=3)
                    folder_download = gr.File(
                        label="Download Folder", visible=False, interactive=False, scale=2)
                    trace_link = gr.HTML(
                        value="",
                        visible=False
                    )
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
            # Also return updated input list with newly uploaded files selected
            all_media = _list_media_in_input()
            return status, gr.update(choices=all_media, value=saved)

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

        def _create_folder_zip(basename: str) -> str | None:
            """Create a zip file of the entire output folder for a basename."""
            if not basename:
                return None
            base_dir = OUTPUT_DIR / basename
            if not base_dir.exists() or not base_dir.is_dir():
                return None
            
            # Create a temporary zip file
            temp_dir = Path(tempfile.gettempdir())
            zip_path = temp_dir / f"{basename}.zip"
            
            # Create zip archive
            shutil.make_archive(
                str(zip_path.with_suffix('')),  # base name without .zip
                'zip',  # archive format
                base_dir.parent,  # root directory
                basename  # base directory to archive
            )
            
            return str(zip_path) if zip_path.exists() else None

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
                # Folder download
                zip_path = _create_folder_zip(basename)
                folder_visible = zip_path is not None
                
                # Check if trace_id exists in JSON
                json_path = base_dir / f"{basename}.json"
                trace_html = ""
                trace_visible = False
                if json_path.exists():
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        trace_id = json_data.get('trace_id')
                        if trace_id:
                            url = f"https://platform.openai.com/logs/trace?trace_id={trace_id}"
                            trace_html = f'''
                            <div style="display: flex; align-items: center; height: 100%; padding-top: 24px;">
                                <button onclick="window.open('{url}', '_blank')" 
                                    style="
                                        background-color: #fff0dd;
                                        color: #ff6e00;
                                        border: 1px solid #ffd9b3;
                                        padding: 8px 12px;
                                        border-radius: 8px;
                                        cursor: pointer;
                                        font-size: 13px;
                                        font-weight: 500;
                                        white-space: nowrap;
                                        transition: all 0.2s;
                                    "
                                    onmouseover="this.style.backgroundColor='#ffe4c4'; this.style.borderColor='#ffb366'"
                                    onmouseout="this.style.backgroundColor='#fff0dd'; this.style.borderColor='#ffd9b3'"
                                >
                                    🔍 View Trace
                                </button>
                            </div>
                            '''
                            trace_visible = True
                    except:
                        pass
            else:
                md_display, media_path, txt_text, srt_text = "", None, "", ""
                zip_path, folder_visible = None, False
                trace_html = ""
                trace_visible = False
            
            # Update dropdown choices dynamically
            current_basenames = _list_basenames()
            dropdown_update = gr.update(
                choices=current_basenames,
                value=basename if basename in current_basenames else (current_basenames[0] if current_basenames else None)
            )
            
            return (
                dropdown_update,
                gr.update(value=md_display),
                gr.update(value=media_path),
                gr.update(value=txt_text),
                gr.update(value=srt_text),
                gr.update(value=zip_path, visible=folder_visible),
                gr.update(value=trace_html, visible=trace_visible),
            )

        base_list.change(_load_all_previews, inputs=base_list,
                         outputs=[base_list, md_preview, md_video, txt_code, srt_code, folder_download, trace_link])

        # Initialize preview on page load if there's a default selection
        demo.load(_load_all_previews, inputs=base_list,
                  outputs=[base_list, md_preview, md_video, txt_code, srt_code, folder_download, trace_link])

        # Run pipeline for selected inputs only
        async def on_run(selected: List[str], transcribe_method: str, prompt_variant: str, notes: str):
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
            yield step(f"Transcription method: {transcribe_method}"), gr.update(), gr.update()
            
            try:
                # Process each file with unified trace workflow
                yield step("Starting unified pipelines (transcribe -> research -> summarize)..."), gr.update(), gr.update()
                
                # Limit concurrency to avoid spawning too many MCP servers at once
                max_parallel = 2
                sem = asyncio.Semaphore(max_parallel)
                
                # Store trace URLs and status updates for display
                trace_urls = {}
                status_messages = []
                
                def log_status(msg: str):
                    """Thread-safe status logging"""
                    status_messages.append(msg)
                
                async def process_one_complete(media_file: str) -> tuple[str, str | None, str | None]:
                    """Process one media file through the complete pipeline with unified trace"""
                    fname_with_ext = Path(media_file).name
                    fname = Path(media_file).stem
                    
                    # Create unified trace workflow for this file
                    t = trace(
                        workflow_name=f"video2MD: {fname}",
                        group_id=fname
                    )
                    
                    # Store trace URL immediately
                    trace_url = f"https://platform.openai.com/logs/trace?trace_id={t.trace_id}"
                    trace_urls[fname] = trace_url
                    
                    with t:
                        async with sem:
                            try:
                                # Step 1: Transcribe
                                log_status(f"[{fname}] 🎤 Starting transcription ({transcribe_method})...")
                                srts = await whisper_host(
                                    input_dir=str(INPUT_DIR),
                                    selected_files=[media_file],
                                    transcribe_method=transcribe_method,
                                    enable_trace=False  # Disable internal trace
                                )
                                
                                if not srts:
                                    log_status(f"[{fname}] ❌ Transcription failed")
                                    return fname, None, t.trace_id
                                
                                srt_path = srts[0]
                                log_status(f"[{fname}] ✅ Transcription completed")
                                
                                # Step 2: Research
                                log_status(f"[{fname}] 🔍 Starting research ({prompt_variant})...")
                                research_res = await research_host(
                                    [srt_path],
                                    prompt_variant=prompt_variant,
                                    user_notes=notes,
                                    enable_trace=False  # Disable internal trace
                                )
                                log_status(f"[{fname}] ✅ Research completed")
                                
                                # Step 3: Summarize
                                log_status(f"[{fname}] 📝 Starting summarization...")
                                md_paths = await summarize_host(
                                    [srt_path],
                                    research_res,
                                    enable_trace=False  # Disable internal trace
                                )
                                
                                md_path = md_paths[0] if md_paths else None
                                
                                if md_path:
                                    log_status(f"[{fname}] ✅ Summarization completed")
                                    
                                    # Save trace_id to JSON file
                                    json_path = OUTPUT_DIR / fname / f"{fname}.json"
                                    if json_path.exists():
                                        try:
                                            with open(json_path, 'r', encoding='utf-8') as f:
                                                json_data = json.load(f)
                                            json_data['trace_id'] = t.trace_id
                                            with open(json_path, 'w', encoding='utf-8') as f:
                                                json.dump(json_data, f, ensure_ascii=False, indent=2)
                                            log_status(f"[{fname}] 💾 Saved trace_id to JSON")
                                        except Exception as e:
                                            print(f"Error saving trace_id to JSON: {e}")
                                else:
                                    log_status(f"[{fname}] ⚠️  Summarization produced no output")
                                
                                return fname, md_path, t.trace_id
                                
                            except Exception as e:
                                log_status(f"[{fname}] ❌ Error: {e}")
                                print(f"Error processing {fname}: {e}")
                                return fname, None, t.trace_id
                
                # Launch all tasks
                tasks = [asyncio.create_task(process_one_complete(f)) for f in selected]
                
                # Give tasks a moment to create trace objects and populate trace_urls
                await asyncio.sleep(0.1)
                
                # Display trace URLs for all files being processed
                if trace_urls:
                    yield step("=" * 60), gr.update(), gr.update()
                    for fname, url in trace_urls.items():
                        yield step(f"🔍 Trace for {fname}:\n   {url}"), gr.update(), gr.update()
                    yield step("=" * 60), gr.update(), gr.update()
                
                # Monitor status updates while tasks are running
                completed = 0
                summaries_created: list[str] = []
                last_status_count = 0
                
                while tasks:
                    # Check for new status messages
                    if len(status_messages) > last_status_count:
                        for msg in status_messages[last_status_count:]:
                            yield step(msg), gr.update(), gr.update()
                        last_status_count = len(status_messages)
                    
                    # Check for completed tasks
                    done, tasks = await asyncio.wait(tasks, timeout=0.5, return_when=asyncio.FIRST_COMPLETED)
                    
                    for task in done:
                        fname, md_path, trace_id = await task
                        completed += 1
                        if md_path:
                            summaries_created.append(md_path)
                            msg = f"🎉 [{completed}/{len(selected)}] Complete: {fname} -> {md_path}"
                        else:
                            msg = f"❌ [{completed}/{len(selected)}] Failed: {fname}"
                        
                        yield step(msg), gr.update(choices=_list_basenames()), gr.update(choices=_list_media_in_input(), value=[])
                
                # Display any remaining status messages
                if len(status_messages) > last_status_count:
                    for msg in status_messages[last_status_count:]:
                        yield step(msg), gr.update(), gr.update()
                
                # Final summary
                if summaries_created:
                    yield (
                        step("All pipelines completed."),
                        gr.update(choices=_list_basenames()),
                        gr.update(choices=_list_media_in_input(), value=[]),
                    )
                else:
                    yield (
                        step("Pipelines completed, but no Markdown files were generated."),
                        gr.update(choices=_list_basenames()),
                        gr.update(choices=_list_media_in_input(), value=[]),
                    )
            except Exception as e:
                # On error: sync input and basename lists to avoid stale selections
                yield step(f"Error occurred: {e}"), gr.update(choices=_list_basenames()), gr.update(choices=_list_media_in_input(), value=[])

        # Note: on_run now returns three outputs: logs, basename dropdown, and input file checkbox group
        run_btn.click(on_run, inputs=[input_files, transcribe_method, prompt_select, user_notes],
                      outputs=[log_output, base_list, input_files])
        
        # URL download handler
        async def on_url_download(topic: str, url: str):
            """Handle URL download only."""
            log_content = ""
            
            def step(msg: str) -> str:
                nonlocal log_content
                log_content += msg + "\n"
                return log_content
            
            # Validate topic name first
            if not topic or not topic.strip():
                yield step("❌ Please enter a topic name"), gr.update()
                return
            
            if not url or not url.strip():
                yield step("❌ Please enter a video URL."), gr.update()
                return
            
            yield step(f"🔗 Processing URL: {url}"), gr.update()
            
            # Create a queue for logs to enable real-time streaming
            import asyncio
            log_queue = asyncio.Queue()
            
            def log_callback(msg: str):
                log_queue.put_nowait(msg)
            
            # Run processing in a separate task
            async def process_task():
                try:
                    video_path, status = await download_video_task(
                        url=url,
                        topic_name=topic,
                        progress_callback=log_callback,
                    )
                    log_queue.put_nowait(("DONE", status))
                except Exception as e:
                    log_queue.put_nowait(("ERROR", str(e)))
                finally:
                    log_queue.put_nowait(None) # Sentinel

            # Start the background task
            task = asyncio.create_task(process_task())
            
            # Consume logs from queue and yield to UI
            while True:
                # Wait for next log message
                msg = await log_queue.get()
                
                if msg is None:
                    break
                
                if isinstance(msg, tuple):
                    type_, content = msg
                    if type_ == "DONE":
                        yield step(content), gr.update(choices=_list_media_in_input())
                    elif type_ == "ERROR":
                        yield step(f"❌ Error: {content}"), gr.update(choices=_list_media_in_input())
                else:
                    # Regular log message
                    yield step(msg), gr.update()
            
            # Ensure task is finished
            await task
        
        url_run_btn.click(
            on_url_download,
            inputs=[topic_input, url_input],
            outputs=[url_log_output, input_files],
        )
        
        # URL input platform detection (on change)
        def on_url_change(url: str):
            
            if DOWNLOADERS_AVAILABLE:
                platform = detect_platform(url)
                if platform:
                    platform_name = SUPPORTED_PLATFORMS.get(platform, platform.value)
                    return gr.update(value=f"✅ **Platform**: {platform_name}", visible=True)
                else:
                    return gr.update(value="⚠️ **Unsupported platform**", visible=True)
            else:
                return gr.update(value="⚠️ **Downloaders not available**", visible=True)
        
        url_input.change(on_url_change, inputs=[url_input], outputs=[detected_platform])

        # Timer: background refresh for input list to reduce manual refresh actions
        def _auto_refresh_inputs():
            return gr.update(choices=_list_media_in_input())

        try:
            timer = gr.Timer(3.0, active=True)
            timer.tick(_auto_refresh_inputs, outputs=input_files)
        except Exception:
            # Older Gradio versions may not have Timer; ignore if unavailable
            pass

    demo.launch(server_name="0.0.0.0", show_error=True, inbrowser=False, favicon_path="ui/video2MD_logo_256.png", allowed_paths=["ui"])


if __name__ == "__main__":  # pragma: no cover - manual run only
    main()
