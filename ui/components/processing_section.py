"""
Processing Section Component for Gradio UI.

Provides the processing settings panel:
- Media file selection
- Transcription method selection
- Research prompt selection
- User notes input
- Run button with processing pipeline
- Files tab (uses file_operations module)
"""

from pathlib import Path
import asyncio
import json
from typing import List

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover
    gr = None

from .shared import INPUT_DIR, OUTPUT_DIR, list_media_in_input, list_basenames
from .file_operations import (
    create_file_operations_tab,
    wire_file_operations_events,
    create_refresh_function,
    get_refresh_outputs,
)

# Import orchestrators from the main app
try:
    from video2md.agents import whisper_host, research_host, summarize_host
    from agents import trace
    ORCHESTRATORS_AVAILABLE = True
except ImportError:
    ORCHESTRATORS_AVAILABLE = False


# ============================================================
# Component Builder
# ============================================================

def create_processing_section() -> dict:
    """
    Create the Processing Settings section components.
    
    Returns a dictionary of Gradio components for external wiring.
    """
    if gr is None:
        return {}
    
    components = {}
    
    with gr.Column(scale=1, min_width=280):
        gr.Markdown("### Processing Settings")
        
        with gr.Tabs() as settings_tabs:
            components["settings_tabs"] = settings_tabs
            
            # Tab 1: Settings
            with gr.TabItem("⚙️ Settings", id="settings_tab"):
                components["input_files"] = gr.CheckboxGroup(
                    choices=list_media_in_input(),
                    label="Select media files",
                )
                
                with gr.Row():
                    components["transcribe_method"] = gr.Radio(
                        choices=[
                            ("Local Whisper (faster-whisper)", "local"),
                            ("OpenAI Whisper API (whisper-1)", "openai"),
                        ],
                        value="openai",
                        label="Transcription Method",
                    )

                    components["prompt_select"] = gr.Dropdown(
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

                components["user_notes"] = gr.Textbox(
                    lines=4,
                    label="User notes (optional)",
                    info="Add author comments, product model numbers, repo URLs, or any hints.",
                )
                
                components["run_btn"] = gr.Button("Go", variant="primary")
                
                components["log_output"] = gr.Textbox(
                    label="Logs",
                    lines=10,
                    max_lines=20,
                    interactive=False,
                )
            
            # Tab 2: Files
            with gr.TabItem("📂 Files", id="files_tab"):
                file_ops_components = create_file_operations_tab()
                components["file_ops"] = file_ops_components
    
    return components


# ============================================================
# Event Wiring
# ============================================================

def wire_processing_events(
    components: dict,
    external_base_list=None,
    demo=None,
):
    """
    Wire up event handlers for processing components.
    
    Args:
        components: Dictionary from create_processing_section
        external_base_list: External dropdown for preview basename
        demo: Gradio Blocks instance for demo.load
    """
    if gr is None or not components:
        return
    
    # Wire file operations
    file_ops = components.get("file_ops", {})
    if file_ops:
        wire_file_operations_events(
            file_ops,
            external_input_files_component=components["input_files"],
            external_base_list_component=external_base_list,
        )
        
        # Refresh Files tab on page load
        refresh_files = create_refresh_function(file_ops)
        if refresh_files and demo is not None:
            demo.load(
                refresh_files,
                outputs=get_refresh_outputs(file_ops),
            )
    
    # The on_run handler needs to be wired with access to orchestrators
    # This is done in app.py since it needs components from other sections
    
    return components


def create_on_run_handler(list_basenames_func, list_media_func):
    """
    Create the on_run handler for processing pipeline.
    
    This needs orchestrators from video2md.agents.
    Returns the async handler function.
    """
    if not ORCHESTRATORS_AVAILABLE:
        async def on_run_disabled(*args):
            yield "❌ Orchestrators not available. Please check dependencies.", gr.update(), gr.update()
        return on_run_disabled
    
    async def on_run(selected: List[str], transcribe_method: str, prompt_variant: str, notes: str):
        log = ""

        def step(msg: str):
            nonlocal log
            log += msg + "\n"
            return log

        if not selected:
            yield step("No input files selected."), gr.update(), gr.update()
            return

        yield step(f"Start processing {len(selected)} file(s): {', '.join(selected)}"), gr.update(), gr.update()
        yield step(f"Transcription method: {transcribe_method}"), gr.update(), gr.update()
        
        try:
            yield step("Starting unified pipelines (transcribe -> research -> summarize)..."), gr.update(), gr.update()
            
            max_parallel = 2
            sem = asyncio.Semaphore(max_parallel)
            
            trace_urls = {}
            status_messages = []
            
            def log_status(msg: str):
                status_messages.append(msg)
            
            async def process_one_complete(media_file: str) -> tuple:
                fname_with_ext = Path(media_file).name
                fname = Path(media_file).stem
                
                t = trace(
                    workflow_name=f"video2MD: {fname}",
                    group_id=fname
                )
                
                trace_url = f"https://platform.openai.com/logs/trace?trace_id={t.trace_id}"
                trace_urls[fname] = trace_url
                
                with t:
                    async with sem:
                        try:
                            log_status(f"[{fname}] 🎤 Starting transcription ({transcribe_method})...")
                            srts = await whisper_host(
                                input_dir=str(INPUT_DIR),
                                selected_files=[media_file],
                                transcribe_method=transcribe_method,
                                enable_trace=False
                            )
                            
                            if not srts:
                                log_status(f"[{fname}] ❌ Transcription failed")
                                return fname, None, t.trace_id
                            
                            srt_path = srts[0]
                            log_status(f"[{fname}] ✅ Transcription completed")
                            
                            log_status(f"[{fname}] 🔍 Starting research ({prompt_variant})...")
                            research_res = await research_host(
                                [srt_path],
                                prompt_variant=prompt_variant,
                                user_notes=notes,
                                enable_trace=False
                            )
                            log_status(f"[{fname}] ✅ Research completed")
                            
                            log_status(f"[{fname}] 📝 Starting summarization...")
                            md_paths = await summarize_host(
                                [srt_path],
                                research_res,
                                enable_trace=False
                            )
                            
                            md_path = md_paths[0] if md_paths else None
                            
                            if md_path:
                                log_status(f"[{fname}] ✅ Summarization completed")
                                
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
            
            tasks = [asyncio.create_task(process_one_complete(f)) for f in selected]
            
            await asyncio.sleep(0.1)
            
            if trace_urls:
                yield step("=" * 60), gr.update(), gr.update()
                for fname, url in trace_urls.items():
                    yield step(f"🔍 Trace for {fname}:\n   {url}"), gr.update(), gr.update()
                yield step("=" * 60), gr.update(), gr.update()
            
            completed = 0
            summaries_created = []
            last_status_count = 0
            
            while tasks:
                if len(status_messages) > last_status_count:
                    for msg in status_messages[last_status_count:]:
                        yield step(msg), gr.update(), gr.update()
                    last_status_count = len(status_messages)
                
                done, tasks = await asyncio.wait(tasks, timeout=0.5, return_when=asyncio.FIRST_COMPLETED)
                
                for task in done:
                    fname, md_path, trace_id = await task
                    completed += 1
                    if md_path:
                        summaries_created.append(md_path)
                        msg = f"🎉 [{completed}/{len(selected)}] Complete: {fname} -> {md_path}"
                    else:
                        msg = f"❌ [{completed}/{len(selected)}] Failed: {fname}"
                    
                    yield step(msg), gr.update(choices=list_basenames_func()), gr.update(choices=list_media_func(), value=[])
            
            if len(status_messages) > last_status_count:
                for msg in status_messages[last_status_count:]:
                    yield step(msg), gr.update(), gr.update()
            
            if summaries_created:
                yield (
                    step("All pipelines completed."),
                    gr.update(choices=list_basenames_func()),
                    gr.update(choices=list_media_func(), value=[]),
                )
            else:
                yield (
                    step("Pipelines completed, but no Markdown files were generated."),
                    gr.update(choices=list_basenames_func()),
                    gr.update(choices=list_media_func(), value=[]),
                )
        except Exception as e:
            yield step(f"Error occurred: {e}"), gr.update(choices=list_basenames_func()), gr.update(choices=list_media_func(), value=[])
    
    return on_run
