"""Reusable UI components for the Gradio app."""

# Shared utilities
from .shared import (
    INPUT_DIR,
    OUTPUT_DIR,
    MEDIA_EXTENSIONS,
    VIDEO_EXTENSIONS,
    list_media_in_input,
    list_basenames,
    is_video_file,
    read_text_file,
    extract_media_path_from_md,
    sanitize_md_for_display,
)

# File operations
from .file_operations import (
    list_input_files,
    list_output_folders,
    get_input_file_path,
    delete_input_file,
    create_output_folder_zip,
    delete_output_folder,
    create_file_operations_tab,
    wire_file_operations_events,
    create_refresh_function,
    get_refresh_outputs,
)

# Input section
from .input_section import (
    create_input_section,
    wire_input_events,
    handle_upload,
    download_video_task,
)

# Processing section
from .processing_section import (
    create_processing_section,
    wire_processing_events,
    create_on_run_handler,
)

# Preview section
from .preview_section import (
    create_preview_section,
    wire_preview_events,
    create_folder_zip,
    get_trace_url,
)

__all__ = [
    # Shared
    "INPUT_DIR",
    "OUTPUT_DIR",
    "MEDIA_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "list_media_in_input",
    "list_basenames",
    "is_video_file",
    "read_text_file",
    "extract_media_path_from_md",
    "sanitize_md_for_display",
    # File operations
    "list_input_files",
    "list_output_folders",
    "get_input_file_path",
    "delete_input_file",
    "create_output_folder_zip",
    "delete_output_folder",
    "create_file_operations_tab",
    "wire_file_operations_events",
    "create_refresh_function",
    "get_refresh_outputs",
    # Input section
    "create_input_section",
    "wire_input_events",
    "handle_upload",
    "download_video_task",
    # Processing section
    "create_processing_section",
    "wire_processing_events",
    "create_on_run_handler",
    # Preview section
    "create_preview_section",
    "wire_preview_events",
    "create_folder_zip",
    "get_trace_url",
]
