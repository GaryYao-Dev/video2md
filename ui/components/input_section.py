"""
Input Section Component for Gradio UI.

Provides the input panel for:
- Local file upload
- URL download (YouTube, Bilibili, Douyin, TikTok)
"""

from pathlib import Path
import json
import re
import shutil
import tempfile
from typing import List, Optional, Tuple

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover
    gr = None

from .shared import INPUT_DIR, OUTPUT_DIR, list_media_in_input, is_video_file

# Import downloaders if available
try:
    from video2md.downloaders import (
        get_downloader,
        detect_platform,
        Platform,
        SUPPORTED_PLATFORMS,
        DownloadError,
        PlatformNotSupportedError,
    )
    DOWNLOADERS_AVAILABLE = True
except ImportError:
    DOWNLOADERS_AVAILABLE = False
    detect_platform = lambda x: None
    Platform = None
    SUPPORTED_PLATFORMS = {}


# ============================================================
# Download Functions
# ============================================================

async def download_video_task(
    url: str,
    topic_name: str = "",
    progress_callback: Optional[callable] = None,
    cookie: Optional[str] = None,
) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Download video from URL to input directory.
    
    Args:
        url: Video URL to download
        topic_name: User-provided topic name for the video (required)
        progress_callback: Optional callback for progress updates
        cookie: Optional cookie string for authenticated downloads
    
    Returns:
        Tuple of (video_path, status_message, video_title)
    """
    if not DOWNLOADERS_AVAILABLE:
        return None, "❌ URL downloaders not available. Please check dependencies.", None
    
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        print(msg)
    
    url = url.strip()
    if not url:
        return None, "❌ Please enter a video URL.", None
    
    # Validate topic name
    topic_name = topic_name.strip()
    if not topic_name:
        return None, "❌ Please enter a topic name for the video", None
    
    # Sanitize topic name for use as directory/file name
    safe_topic_name = re.sub(r'[<>:"/\\|?*]', '_', topic_name)
    safe_topic_name = safe_topic_name[:100]  # Limit length
    
    # Detect platform
    platform = detect_platform(url)
    if platform is None:
        return None, f"❌ Unsupported platform. Supported: {', '.join(p.value for p in SUPPORTED_PLATFORMS.keys())}", None
    
    platform_name = SUPPORTED_PLATFORMS.get(platform, platform.value)
    log(f"🔍 Detected platform: {platform_name}")
    log(f"📁 Topic: {topic_name}")
    
    try:
        # Get downloader
        downloader = get_downloader(url)
        
        # Create output directory for metadata
        final_output_dir = OUTPUT_DIR / safe_topic_name
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            log(f"⬇️ Downloading video from {platform_name}...")
            
            # Progress hook for downloader
            def download_progress_hook(d):
                if d.get('status') == 'downloading':
                    def strip_ansi(s):
                        return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)

                    percent_str = strip_ansi(d.get('_percent_str', '')).strip()
                    speed_str = strip_ansi(d.get('_speed_str', '')).strip()
                    eta_str = strip_ansi(d.get('_eta_str', '')).strip()
                    
                    if percent_str and '%' in percent_str:
                        try:
                            p_val = float(percent_str.replace('%', ''))
                            
                            should_log = False
                            if 0.0 <= p_val < 0.1: should_log = True
                            elif 33.0 <= p_val <= 34.0: should_log = True
                            elif 66.0 <= p_val <= 67.0: should_log = True
                            elif p_val >= 99.9: should_log = True
                            
                            if should_log:
                                log(f"⬇️ Downloading: {percent_str} (Speed: {speed_str}, ETA: {eta_str})")
                        except ValueError:
                            pass
            
            result = await downloader.download(url, temp_path, progress_hook=download_progress_hook, cookie=cookie)
            
            video_path = result.file_path
            video_ext = video_path.suffix or ".mp4"
            
            input_video_path = INPUT_DIR / f"{safe_topic_name}{video_ext}"
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
            
            return str(input_video_path), f"✅ Ready to process: {safe_topic_name}", result.title

    except PlatformNotSupportedError as e:
        return None, f"❌ Platform not supported: {e}", None
    except DownloadError as e:
        return None, f"❌ Download failed: {e}", None
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, f"❌ Error: {e}", None


# ============================================================
# Upload Handler
# ============================================================

def handle_upload(files) -> Tuple[str, object]:
    """
    Handle file upload and move to input directory.
    
    Returns:
        Tuple of (status_message, input_files_update)
    """
    if not files:
        return ("No file selected.", gr.update())
    
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    wrong = []
    
    for f in (files if isinstance(files, list) else [files]):
        path = Path(getattr(f, "name", f))
        if not is_video_file(path.name):
            wrong.append(path.name)
            continue
        dest = INPUT_DIR / path.name
        try:
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
    
    all_media = list_media_in_input()
    return status, gr.update(choices=all_media, value=saved)


# ============================================================
# Component Builder
# ============================================================

def create_input_section() -> dict:
    """
    Create the Input section components.
    
    Returns a dictionary of Gradio components for external wiring.
    """
    if gr is None:
        return {}
    
    components = {}
    
    with gr.Column(scale=1, min_width=280):
        gr.Markdown("### File Input")
        
        with gr.Tabs() as input_tabs:
            components["input_tabs"] = input_tabs
            
            # Tab 1: File Upload
            with gr.TabItem("📁 Local Files", id="file_tab"):
                components["upload_files"] = gr.File(
                    label="Upload videos", file_count="multiple"
                )
                components["upload_status"] = gr.Markdown(visible=True)
            
            # Tab 2: URL Download
            with gr.TabItem("🔗 Video URL", id="url_tab"):
                gr.Markdown("""
                **Supported Platforms**: Bilibili, YouTube, Douyin(Cookie Required), TikTok(Cookie Required)
                """)
                components["topic_input"] = gr.Textbox(
                    label="Topic Name *Required*",
                    placeholder="e.g., Python_Tutorial, Product_Demo...",
                    lines=1,
                )
                components["url_input"] = gr.Textbox(
                    label="Video URL",
                    placeholder="https://www.bilibili.com/video/BVxxxxx\nhttps://youtu.be/xxxxx\nhttps://www.douyin.com/video/xxxxx",
                    lines=4,
                )
                components["cookie_input"] = gr.Textbox(
                    label="Cookie for Douyin/TikTok",
                    placeholder="Paste cookie string here if download fails",
                    lines=2,
                    visible=False,
                    max_lines=2,
                )
                components["detected_platform"] = gr.Markdown(value="", visible=False)
                
                components["url_run_btn"] = gr.Button("Download to Input", variant="primary")
                components["url_log_output"] = gr.Textbox(
                    label="Download Logs", lines=2, max_lines=3, interactive=False
                )
    
    return components


# ============================================================
# Event Wiring
# ============================================================

def wire_input_events(components: dict, external_input_files=None, external_user_notes=None):
    """
    Wire up event handlers for input components.
    
    Args:
        components: Dictionary from create_input_section
        external_input_files: External CheckboxGroup for input files
        external_user_notes: External Textbox for user notes
    """
    if gr is None or not components:
        return
    
    # Upload handler
    def _handle_upload_wrapper(files):
        return handle_upload(files)
    
    components["upload_files"].change(
        _handle_upload_wrapper,
        inputs=[components["upload_files"]],
        outputs=[components["upload_status"], external_input_files] if external_input_files else [components["upload_status"]]
    )
    
    if hasattr(components["upload_files"], "upload"):
        components["upload_files"].upload(
            _handle_upload_wrapper,
            inputs=[components["upload_files"]],
            outputs=[components["upload_status"], external_input_files] if external_input_files else [components["upload_status"]]
        )
    
    # URL download handler
    async def on_url_download(topic: str, url: str, cookie: str):
        """Handle URL download."""
        import asyncio
        
        log_content = ""
        
        def step(msg: str) -> str:
            nonlocal log_content
            log_content += msg + "\n"
            return log_content
        
        if not topic or not topic.strip():
            yield step("❌ Please enter a topic name"), gr.update(), gr.update(), gr.update()
            return
        
        if not url or not url.strip():
            yield step("❌ Please enter a video URL."), gr.update(), gr.update(), gr.update()
            return
        
        yield step(f"🔗 Processing URL: {url}"), gr.update(), gr.update(), gr.update()
        
        log_queue = asyncio.Queue()
        
        def log_callback(msg: str):
            log_queue.put_nowait(msg)
        
        async def process_task():
            try:
                video_path, status, title = await download_video_task(
                    url=url,
                    topic_name=topic,
                    progress_callback=log_callback,
                    cookie=cookie.strip() if cookie else None,
                )
                log_queue.put_nowait(("DONE", (status, title)))
            except Exception as e:
                log_queue.put_nowait(("ERROR", str(e)))
            finally:
                log_queue.put_nowait(None)

        task = asyncio.create_task(process_task())
        
        while True:
            msg = await log_queue.get()
            
            if msg is None:
                break
            
            if isinstance(msg, tuple):
                type_, content = msg
                if type_ == "DONE":
                    status_msg, title = content
                    note_update = gr.update(value=title) if title else gr.update()
                    yield step(status_msg), gr.update(choices=list_media_in_input()), gr.update(), note_update
                elif type_ == "ERROR":
                    yield step(f"❌ Error: {content}"), gr.update(choices=list_media_in_input()), gr.update(), gr.update()
            else:
                yield step(msg), gr.update(), gr.update(), gr.update()
        
        await task
    
    download_outputs = [
        components["url_log_output"],
        external_input_files if external_input_files else components["url_log_output"],
        components["cookie_input"],
        external_user_notes if external_user_notes else components["url_log_output"],
    ]
    
    components["url_run_btn"].click(
        on_url_download,
        inputs=[components["topic_input"], components["url_input"], components["cookie_input"]],
        outputs=download_outputs,
    )
    
    # Cookie handling via LocalStorage
    js_save_cookie = """
    (val) => {
        if (val) {
            localStorage.setItem("video2md_douyin_cookie", val);
        }
        return val;
    }
    """
    components["cookie_input"].input(None, inputs=[components["cookie_input"]], js=js_save_cookie)
    
    # URL platform detection
    def on_url_change(url: str):
        if DOWNLOADERS_AVAILABLE:
            platform = detect_platform(url)
            if platform:
                platform_name = SUPPORTED_PLATFORMS.get(platform, platform.value)
                is_douyin_tiktok = platform in (Platform.DOUYIN, Platform.TIKTOK)
                return (
                    gr.update(value=f"✅ **Platform**: {platform_name}", visible=True),
                    gr.update(visible=is_douyin_tiktok),
                )
            else:
                return (
                    gr.update(value="⚠️ **Unsupported platform**", visible=True),
                    gr.update(visible=False),
                )
        else:
            return (
                gr.update(value="⚠️ **Downloaders not available**", visible=True),
                gr.update(visible=False),
            )
    
    js_load_cookie = """
    (url) => {
        if (url.includes('douyin') || url.includes('tiktok')) {
            return localStorage.getItem("video2md_douyin_cookie") || "";
        }
        return "";
    }
    """
    
    components["url_input"].change(
        on_url_change,
        inputs=[components["url_input"]],
        outputs=[components["detected_platform"], components["cookie_input"]],
    ).then(
        None,
        inputs=[components["url_input"]],
        outputs=[components["cookie_input"]],
        js=js_load_cookie
    )
