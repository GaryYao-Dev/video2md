"""
File Operations Component for Gradio UI.

Provides UI components and handlers for managing input/output files:
- List files in input/output directories
- Download files/folders
- Delete files/folders

Following SOLID principles - Single Responsibility for file operations.
"""

from pathlib import Path
import shutil
import tempfile
from typing import List, Optional, Tuple, Callable

try:
    import gradio as gr  # type: ignore
except Exception:  # pragma: no cover
    gr = None


# Default directories (can be overridden)
INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")


# ============================================================
# Helper Functions - File Listing
# ============================================================

def list_input_files() -> List[str]:
    """List all media files in the input directory."""
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


def list_output_folders() -> List[str]:
    """List all output folders that contain processed files."""
    names = []
    if OUTPUT_DIR.exists():
        for sub in sorted(OUTPUT_DIR.iterdir()):
            if not sub.is_dir():
                continue
            name = sub.name
            # Check if folder has any expected output files
            if (sub / f"{name}.md").exists() or (sub / f"{name}.txt").exists() or (sub / f"{name}.srt").exists() or (sub / f"{name}.json").exists():
                names.append(name)
    return names


# ============================================================
# Helper Functions - File Operations
# ============================================================

def get_input_file_path(filename: str) -> Optional[str]:
    """Get the full path of an input file for download."""
    if not filename:
        return None
    file_path = INPUT_DIR / filename
    if file_path.exists() and file_path.is_file():
        return str(file_path)
    return None


def delete_input_file(filename: str) -> Tuple[str, List[str]]:
    """
    Delete a file from the input directory.
    
    Returns:
        Tuple of (status_message, updated_file_list)
    """
    if not filename:
        return "⚠️ No file selected", list_input_files()
    
    file_path = INPUT_DIR / filename
    if not file_path.exists():
        return f"⚠️ File not found: {filename}", list_input_files()
    
    try:
        file_path.unlink()
        return f"✅ Deleted: {filename}", list_input_files()
    except Exception as e:
        return f"❌ Error deleting {filename}: {e}", list_input_files()


def create_output_folder_zip(basename: str) -> Optional[str]:
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


def delete_output_folder(basename: str) -> Tuple[str, List[str]]:
    """
    Delete an output folder and all its contents.
    
    Returns:
        Tuple of (status_message, updated_folder_list)
    """
    if not basename:
        return "⚠️ No folder selected", list_output_folders()
    
    folder_path = OUTPUT_DIR / basename
    if not folder_path.exists():
        return f"⚠️ Folder not found: {basename}", list_output_folders()
    
    try:
        shutil.rmtree(folder_path)
        return f"✅ Deleted folder: {basename}", list_output_folders()
    except Exception as e:
        return f"❌ Error deleting {basename}: {e}", list_output_folders()


# ============================================================
# Gradio Component Builder
# ============================================================

def create_file_operations_tab(
    on_input_refresh: Optional[Callable] = None,
    on_output_refresh: Optional[Callable] = None,
) -> dict:
    """
    Create the Files Operations tab components.
    
    Returns a dictionary of Gradio components for external wiring.
    """
    if gr is None:
        return {}
    
    components = {}
    
    # Get initial values
    initial_input_files = list_input_files()
    initial_output_folders = list_output_folders()
    initial_input = initial_input_files[0] if initial_input_files else None
    initial_output = initial_output_folders[0] if initial_output_folders else None
    
    with gr.Column():
        # Input Files Section
        gr.Markdown("#### 📥 Input Files")
        gr.Markdown("Manage media files in the `input/` directory", elem_classes=["text-sm"])
        
        components["input_dropdown"] = gr.Dropdown(
            choices=initial_input_files,
            value=initial_input,
            label="Select Input File",
            interactive=True,
        )
        
        with gr.Row():
            # Use DownloadButton for proper file download with correct name
            components["input_download_btn"] = gr.DownloadButton(
                "⬇️ Download",
                value=get_input_file_path(initial_input) if initial_input else None,
                variant="secondary",
                size="sm",
                visible=bool(initial_input_files),
            )
            components["input_delete_btn"] = gr.Button(
                "🗑️ Delete",
                variant="stop",
                size="sm",
                visible=bool(initial_input_files),
            )
        
        components["input_status"] = gr.Markdown("")
        
        gr.HTML("<hr style='margin: 16px 0; border: none; border-top: 1px solid #ddd;'>")
        
        # Output Folders Section
        gr.Markdown("#### 📤 Output Folders")
        gr.Markdown("Manage processed results in the `output/` directory", elem_classes=["text-sm"])
        
        components["output_dropdown"] = gr.Dropdown(
            choices=initial_output_folders,
            value=initial_output,
            label="Select Output Folder",
            interactive=True,
        )
        
        with gr.Row():
            # Use DownloadButton for proper file download with correct name
            components["output_download_btn"] = gr.DownloadButton(
                "⬇️ Download ZIP",
                value=create_output_folder_zip(initial_output) if initial_output else None,
                variant="secondary",
                size="sm",
                visible=bool(initial_output_folders),
            )
            components["output_delete_btn"] = gr.Button(
                "🗑️ Delete",
                variant="stop",
                size="sm",
                visible=bool(initial_output_folders),
            )
        
        components["output_status"] = gr.Markdown("")
    
    return components


def wire_file_operations_events(
    components: dict,
    external_input_files_component=None,
    external_base_list_component=None,
):
    """
    Wire up event handlers for file operations components.
    
    Args:
        components: Dictionary of Gradio components from create_file_operations_tab
        external_input_files_component: Optional external CheckboxGroup to update when input files change
        external_base_list_component: Optional external Dropdown to update when output folders change
    """
    if gr is None or not components:
        return
    
    # -------------------- Input File Handlers --------------------
    
    # Input file selection -> update download button with file path
    def on_input_select(filename: str):
        has_file = bool(filename)
        file_path = get_input_file_path(filename) if filename else None
        return (
            gr.update(value=file_path, visible=has_file),  # download btn with file
            gr.update(visible=has_file),  # delete btn
        )
    
    components["input_dropdown"].change(
        on_input_select,
        inputs=[components["input_dropdown"]],
        outputs=[components["input_download_btn"], components["input_delete_btn"]],
    )
    
    # Input delete button
    def on_input_delete(filename: str):
        status, updated_list = delete_input_file(filename)
        has_files = bool(updated_list)
        new_file = updated_list[0] if updated_list else None
        new_path = get_input_file_path(new_file) if new_file else None
        return (
            gr.update(choices=updated_list, value=new_file),
            gr.update(value=new_path, visible=has_files),  # download btn
            gr.update(visible=has_files),  # delete btn
            status,
        )
    
    input_delete_outputs = [
        components["input_dropdown"],
        components["input_download_btn"],
        components["input_delete_btn"],
        components["input_status"],
    ]
    
    # Add external component if provided
    if external_input_files_component is not None:
        def on_input_delete_with_external(filename: str):
            status, updated_list = delete_input_file(filename)
            has_files = bool(updated_list)
            new_file = updated_list[0] if updated_list else None
            new_path = get_input_file_path(new_file) if new_file else None
            return (
                gr.update(choices=updated_list, value=new_file),
                gr.update(value=new_path, visible=has_files),
                gr.update(visible=has_files),
                status,
                gr.update(choices=updated_list),
            )
        
        components["input_delete_btn"].click(
            on_input_delete_with_external,
            inputs=[components["input_dropdown"]],
            outputs=input_delete_outputs + [external_input_files_component],
        )
    else:
        components["input_delete_btn"].click(
            on_input_delete,
            inputs=[components["input_dropdown"]],
            outputs=input_delete_outputs,
        )
    
    # -------------------- Output Folder Handlers --------------------
    
    # Output folder selection -> update download button with zip path and sync with external
    def on_output_select(basename: str):
        has_folder = bool(basename)
        zip_path = create_output_folder_zip(basename) if basename else None
        return (
            gr.update(value=zip_path, visible=has_folder),  # download btn with zip
            gr.update(visible=has_folder),  # delete btn
        )
    
    output_select_outputs = [
        components["output_download_btn"],
        components["output_delete_btn"],
    ]
    
    # If we have external_base_list_component, also sync with it
    if external_base_list_component is not None:
        def on_output_select_with_external(basename: str):
            has_folder = bool(basename)
            zip_path = create_output_folder_zip(basename) if basename else None
            return (
                gr.update(value=zip_path, visible=has_folder),
                gr.update(visible=has_folder),
                gr.update(value=basename),  # sync to external dropdown
            )
        
        components["output_dropdown"].change(
            on_output_select_with_external,
            inputs=[components["output_dropdown"]],
            outputs=output_select_outputs + [external_base_list_component],
        )
    else:
        components["output_dropdown"].change(
            on_output_select,
            inputs=[components["output_dropdown"]],
            outputs=output_select_outputs,
        )
    
    # Output delete button
    def on_output_delete(basename: str):
        status, updated_list = delete_output_folder(basename)
        has_folders = bool(updated_list)
        new_folder = updated_list[0] if updated_list else None
        new_zip = create_output_folder_zip(new_folder) if new_folder else None
        return (
            gr.update(choices=updated_list, value=new_folder),
            gr.update(value=new_zip, visible=has_folders),  # download btn
            gr.update(visible=has_folders),  # delete btn
            status,
        )
    
    output_delete_outputs = [
        components["output_dropdown"],
        components["output_download_btn"],
        components["output_delete_btn"],
        components["output_status"],
    ]
    
    # Add external component if provided
    if external_base_list_component is not None:
        def on_output_delete_with_external(basename: str):
            status, updated_list = delete_output_folder(basename)
            has_folders = bool(updated_list)
            new_folder = updated_list[0] if updated_list else None
            new_zip = create_output_folder_zip(new_folder) if new_folder else None
            return (
                gr.update(choices=updated_list, value=new_folder),
                gr.update(value=new_zip, visible=has_folders),
                gr.update(visible=has_folders),
                status,
                gr.update(choices=updated_list, value=new_folder),  # sync to external
            )
        
        components["output_delete_btn"].click(
            on_output_delete_with_external,
            inputs=[components["output_dropdown"]],
            outputs=output_delete_outputs + [external_base_list_component],
        )
    else:
        components["output_delete_btn"].click(
            on_output_delete,
            inputs=[components["output_dropdown"]],
            outputs=output_delete_outputs,
        )


def create_refresh_function(components: dict):
    """
    Create a refresh function for the Files tab dropdowns.
    This can be used with demo.load or timer.tick to keep lists in sync.
    
    Returns a function that refreshes both input and output dropdowns.
    """
    if gr is None or not components:
        return None
    
    def refresh_files_lists():
        """Refresh both input files and output folders dropdowns."""
        input_files = list_input_files()
        output_folders = list_output_folders()
        
        input_value = input_files[0] if input_files else None
        output_value = output_folders[0] if output_folders else None
        
        input_path = get_input_file_path(input_value) if input_value else None
        output_zip = create_output_folder_zip(output_value) if output_value else None
        
        return (
            gr.update(choices=input_files, value=input_value),  # input_dropdown
            gr.update(value=input_path, visible=bool(input_files)),  # input_download_btn
            gr.update(visible=bool(input_files)),  # input_delete_btn
            gr.update(choices=output_folders, value=output_value),  # output_dropdown
            gr.update(value=output_zip, visible=bool(output_folders)),  # output_download_btn
            gr.update(visible=bool(output_folders)),  # output_delete_btn
        )
    
    return refresh_files_lists


def get_refresh_outputs(components: dict) -> list:
    """Get the list of output components for the refresh function."""
    return [
        components["input_dropdown"],
        components["input_download_btn"],
        components["input_delete_btn"],
        components["output_dropdown"],
        components["output_download_btn"],
        components["output_delete_btn"],
    ]
