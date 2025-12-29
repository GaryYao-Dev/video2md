"""
Gradio Frontend - Video2MD

A thin orchestrator that assembles the modular UI components.

Features:
- Upload videos and select media files to process
- Download videos from YouTube, Bilibili, Douyin, TikTok
- Preview Markdown (.md) and TXT/SRT side by side
- Auto-refresh lists after upload and processing

To run locally:
    python ui/app.py
"""

from pathlib import Path
from typing import List
import sys

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover
    gr = None

# Ensure src/ is on sys.path when running from source tree
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.exists():
    sys.path.insert(0, str(_SRC))

# Import components
from components import (
    # Shared
    INPUT_DIR,
    OUTPUT_DIR,
    list_media_in_input,
    list_basenames,
    # Input section
    create_input_section,
    wire_input_events,
    # Processing section
    create_processing_section,
    wire_processing_events,
    create_on_run_handler,
    # Preview section
    create_preview_section,
    wire_preview_events,
)

# Import dependency checker
try:
    from video2md.utils import DependencyChecker
except ImportError:
    class DependencyChecker:
        @staticmethod
        def validate_or_exit(*args, **kwargs):
            pass


def main():  # pragma: no cover
    """Main entry point for the Gradio UI."""
    
    # Check dependencies before starting UI
    print("Checking dependencies...")
    DependencyChecker.validate_or_exit(require_ffmpeg=True, require_node=True)
    
    if gr is None:
        print("Gradio is not installed yet. Install with: pip install gradio>=4")
        return

    with gr.Blocks(
        title="Video2MD", 
        theme=gr.themes.Soft(primary_hue=gr.themes.colors.purple)
    ) as demo:
        
        # Header
        gr.Markdown("# Video2MD")
        gr.Markdown("""
        ### Convert videos to Markdown summaries with transcription and research.
        """)

        with gr.Row():
            # Column 1: Input Section
            input_components = create_input_section()
            
            # Column 2: Processing Section
            processing_components = create_processing_section()
            
            # Column 3: Preview Section
            preview_components = create_preview_section()
        
        # ===== Wire Events =====
        
        # Get key components for cross-section wiring
        input_files = processing_components.get("input_files")
        user_notes = processing_components.get("user_notes")
        base_list = preview_components.get("base_list")
        log_output = processing_components.get("log_output")
        run_btn = processing_components.get("run_btn")
        
        # Wire input section events
        wire_input_events(
            input_components,
            external_input_files=input_files,
            external_user_notes=user_notes,
        )
        
        # Wire processing section events
        wire_processing_events(
            processing_components,
            external_base_list=base_list,
            demo=demo,
        )
        
        # Wire preview section events
        wire_preview_events(
            preview_components,
            demo=demo,
        )
        
        # Wire the Run button (needs cross-section access)
        on_run = create_on_run_handler(list_basenames, list_media_in_input)
        run_btn.click(
            on_run,
            inputs=[
                processing_components["input_files"],
                processing_components["transcribe_method"],
                processing_components["prompt_select"],
                processing_components["user_notes"],
            ],
            outputs=[log_output, base_list, input_files],
        )
        
        # Timer: background refresh for input checkbox only (non-disruptive)
        # Dropdowns sync via demo.load and event handlers (upload/delete/process)
        def _auto_refresh_inputs():
            return gr.update(choices=list_media_in_input())

        try:
            timer = gr.Timer(3.0, active=True)
            timer.tick(_auto_refresh_inputs, outputs=input_files)
        except Exception:
            pass  # Older Gradio versions may not have Timer

    demo.launch(
        server_name="0.0.0.0", 
        show_error=True, 
        inbrowser=False, 
        favicon_path="ui/video2MD_logo_256.png", 
        allowed_paths=["ui"]
    )


if __name__ == "__main__":  # pragma: no cover
    main()
