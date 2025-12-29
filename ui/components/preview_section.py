"""
Preview Section Component for Gradio UI.

Provides the preview panel for Markdown, TXT, and SRT content:
- Dropdown to select processed files
- Media player for video/audio
- Tabbed view for MD/TXT/SRT
- Download folder as ZIP
- View trace link
"""

from pathlib import Path
import json
import re
import shutil
import tempfile
from typing import Optional, Tuple

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover
    gr = None

from .shared import OUTPUT_DIR, list_basenames, read_text_file


# ============================================================
# Helper Functions
# ============================================================

def extract_media_path_from_md(md_text: str, base_dir: Path) -> Optional[str]:
    """Extract embedded media path from markdown content."""
    if not md_text:
        return None
    
    # Try HTML <video src="./media/xxx">
    m = re.search(r'<video[^>]*src=["\']([^"\']+)["\']', md_text, flags=re.IGNORECASE)
    candidate = m.group(1) if m else None
    
    if not candidate:
        # Try HTML <source src="./media/xxx">
        m_src = re.search(r'<source[^>]*src=["\']([^"\']+)["\']', md_text, flags=re.IGNORECASE)
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


def sanitize_md_for_display(md_text: str) -> str:
    """Clean markdown text for display, removing video tags."""
    if not md_text:
        return ""
    cleaned = re.sub(
        r"<video[\s\S]*?</video>", 
        "\n> [Video preview is shown in the player above]\n", 
        md_text, 
        flags=re.IGNORECASE
    )
    return cleaned


def create_folder_zip(basename: str) -> Optional[str]:
    """Create a zip file of the entire output folder for a basename."""
    if not basename:
        return None
    base_dir = OUTPUT_DIR / basename
    if not base_dir.exists() or not base_dir.is_dir():
        return None
    
    temp_dir = Path(tempfile.gettempdir())
    zip_path = temp_dir / f"{basename}.zip"
    
    shutil.make_archive(
        str(zip_path.with_suffix('')),
        'zip',
        base_dir.parent,
        basename
    )
    
    return str(zip_path) if zip_path.exists() else None


def get_trace_url(basename: str) -> Optional[str]:
    """Get trace URL from JSON metadata file."""
    if not basename:
        return None
    json_path = OUTPUT_DIR / basename / f"{basename}.json"
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            trace_id = json_data.get('trace_id')
            if trace_id:
                return f"https://platform.openai.com/logs/trace?trace_id={trace_id}"
        except:
            pass
    return None


# ============================================================
# Component Builder
# ============================================================

def create_preview_section() -> dict:
    """
    Create the Preview section components.
    
    Returns a dictionary of Gradio components for external wiring.
    """
    if gr is None:
        return {}
    
    components = {}
    
    with gr.Column(scale=3):
        gr.Markdown("### Preview")
        
        # Get initial basenames
        initial_basenames = list_basenames()
        initial_value = initial_basenames[0] if initial_basenames else None
        
        # Select filename, Download folder and trace link
        with gr.Row():
            components["base_list"] = gr.Dropdown(
                choices=initial_basenames, 
                value=initial_value,
                label="Select filename",
                scale=3
            )
            with gr.Column(scale=1):
                components["folder_download"] = gr.DownloadButton(
                    "⬇️ Download Folder", visible=False, size="sm"
                )
                components["trace_btn"] = gr.Button(
                    "🔍 View Trace", visible=False, size="sm"
                )
        
        # Responsive player style
        gr.HTML("""
        <style>
        .gradio-container, .gradio-container * { font-family: Arial, sans-serif !important; }
        .gradio-container .cm-editor { height: 40vh !important; }
        .gradio-container .cm-editor .cm-scroller { overflow: auto !important; }
        #md_player video{width:100%;max-width:100%;height:auto;max-height:60vh}
        </style>
        """)
        
        # Media player
        components["md_video"] = gr.Video(
            label="Media Player", interactive=False, elem_id="md_player"
        )
        
        # Preview tabs
        with gr.Tabs():
            with gr.Tab("Markdown"):
                components["md_preview"] = gr.Markdown(
                    "Select a filename above to preview Markdown."
                )
            with gr.Tab("TXT"):
                components["txt_code"] = gr.Code(
                    language=None, label="TXT Preview", interactive=False, lines=18
                )
            with gr.Tab("SRT"):
                components["srt_code"] = gr.Code(
                    language=None, label="SRT Preview", interactive=False, lines=18
                )
    
    return components


# ============================================================
# Event Wiring
# ============================================================

def wire_preview_events(components: dict, demo=None):
    """
    Wire up event handlers for preview components.
    
    Args:
        components: Dictionary of Gradio components from create_preview_section
        demo: The Gradio Blocks instance for demo.load
    """
    if gr is None or not components:
        return
    
    def _read_text_file_local(p: Path) -> str:
        """Read text file with fallback encoding."""
        if not p.exists():
            return ""
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return p.read_text(errors="ignore")
    
    def load_all_previews(basename: str):
        """Load all preview content for a basename."""
        if basename:
            base_dir = OUTPUT_DIR / basename
            md_path = base_dir / f"{basename}.md"
            md_text = _read_text_file_local(md_path)
            md_display = sanitize_md_for_display(md_text) if md_text else "(No Markdown content)"
            media_path = extract_media_path_from_md(md_text, base_dir) if md_text else None
            
            # TXT
            txt_path = base_dir / f"{basename}.txt"
            txt_text = _read_text_file_local(txt_path) or "(No TXT content)"
            
            # SRT
            srt_path = base_dir / f"{basename}.srt"
            srt_text = _read_text_file_local(srt_path) or "(No SRT content)"
            
            # Folder download
            zip_path = create_folder_zip(basename)
            folder_visible = zip_path is not None
            
            # Check trace
            trace_url = get_trace_url(basename)
            trace_visible = trace_url is not None
        else:
            md_display, media_path, txt_text, srt_text = "", None, "", ""
            zip_path, folder_visible = None, False
            trace_visible = False
        
        # Update dropdown choices dynamically
        current_basenames = list_basenames()
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
            gr.update(visible=trace_visible),
        )
    
    preview_outputs = [
        components["base_list"],
        components["md_preview"],
        components["md_video"],
        components["txt_code"],
        components["srt_code"],
        components["folder_download"],
        components["trace_btn"],
    ]
    
    # Wire dropdown change
    components["base_list"].change(
        load_all_previews, 
        inputs=[components["base_list"]],
        outputs=preview_outputs
    )
    
    # Initialize on page load
    if demo is not None:
        demo.load(
            load_all_previews, 
            inputs=[components["base_list"]],
            outputs=preview_outputs
        )
    
    # Trace button click handler
    def on_trace_click(basename: str) -> str:
        return get_trace_url(basename)
    
    components["trace_btn"].click(
        on_trace_click,
        inputs=[components["base_list"]],
        outputs=[],
        js="(basename) => { fetch('/get_trace_url?basename=' + basename).then(r => r.text()).then(url => { if(url) window.open(url, '_blank'); }); }"
    )
    
    return load_all_previews  # Return for external use
