"""
Whisper Server Client Example
Demonstrates how to call Whisper transcription service API
Supports audio and video files (videos are automatically converted to audio)
"""
import requests
from pathlib import Path
import os
import tempfile
import re
from video2md.utils.video_converter import VideoConverter
import dotenv

# Import Chinese converter
try:
    from video2md.utils.chinese_converter import convert_chinese_text
    CHINESE_CONVERSION_AVAILABLE = True
    print("Simplified Chinese conversion available.")
except Exception:
    CHINESE_CONVERSION_AVAILABLE = False
    print("Warning: Chinese converter not available.")

dotenv.load_dotenv(override=True)
whisper_api_url = os.getenv("WHISPER_API_URL", "http://localhost:8000")
print(f"Using Whisper server URL: {whisper_api_url}")


def srt_to_txt(srt_content: str) -> str:
    """
    Convert SRT subtitle content to plain text

    Args:
        srt_content: SRT format content as string

    Returns:
        Plain text content with sentences joined by commas
    """
    # Split content into subtitle blocks
    blocks = re.split(r'\n\s*\n', srt_content.strip())

    sentences = []

    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split('\n')

        # Skip if not enough lines (need at least 3: number, timestamp, text)
        if len(lines) < 3:
            continue

        # Extract text content (skip number and timestamp lines)
        text_lines = lines[2:]  # Skip subtitle number and timestamp
        text_content = ' '.join(text_lines).strip()

        if text_content:
            sentences.append(text_content)

    # Join sentences with commas and add period at the end
    result = '\n'.join(sentences)
    if result and not result.endswith('。'):
        result += '。'

    return result


def convert_srt_file_to_txt(srt_file_path: str, txt_file_path: str = None) -> str:
    """
    Convert SRT file to TXT file

    Args:
        srt_file_path: Path to input SRT file
        txt_file_path: Path to output TXT file (optional)

    Returns:
        Path to the generated TXT file
    """
    srt_path = Path(srt_file_path)

    if not srt_path.exists():
        raise FileNotFoundError(f"SRT file does not exist: {srt_file_path}")

    # Read SRT content
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()

    # Convert to plain text
    txt_content = srt_to_txt(srt_content)

    # Determine output file path
    if txt_file_path is None:
        txt_file_path = str(srt_path.with_suffix('.txt'))

    # Write TXT content
    txt_path = Path(txt_file_path)
    txt_path.parent.mkdir(parents=True, exist_ok=True)

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)

    print(f"SRT converted to TXT: {txt_path}")
    return str(txt_path)


def transcribe_media(
    media_file_path: str,
    server_url: str = whisper_api_url,
    language: str = None,
    output_format: str = "srt",
    task: str = "transcribe",
    initial_prompt: str = None,
    save_path: str = None,
    output_dir: str = "whisper_output",
    keep_temp_audio: bool = False,
    chinese_format: str = "simplified"
):
    """
    Call Whisper server for media file transcription
    Supports audio and video files, video files are automatically converted to audio

    Args:
        media_file_path: Media file path (audio or video)
        server_url: Server URL (default: http://localhost:8000)
        language: Language code (default: zh)
        output_format: Output format (default: srt, options: txt, vtt, tsv, json)
        task: Task type (default: transcribe, options: translate)
        initial_prompt: Initial prompt text
        save_path: Path to save results (optional)
        output_dir: Output directory (optional, default 'whisper_output')
        keep_temp_audio: Whether to keep temporary audio files (default: False)
        chinese_format: Chinese character format (optional, options: "simplified", "traditional")

    Returns:
        Transcription result text
    """
    # Check if file exists
    media_path = Path(media_file_path)
    if not media_path.exists():
        raise FileNotFoundError(
            f"Media file does not exist: {media_file_path}")

    # Initialize converter
    converter = VideoConverter()
    temp_audio_path = None
    audio_file_to_process = None

    try:
        # Check file type and process
        if converter.is_video_file(media_path):
            print(f"Detected video file: {media_path.name}")
            print("Converting to audio format...")

            # Determine audio output directory (temporary files use temp directory)
            audio_output_dir = tempfile.gettempdir(
            ) if not keep_temp_audio else (output_dir or "whisper_output")

            # Convert video to audio
            audio_file_to_process = converter.video_to_audio(
                input_path=media_path,
                output_dir=audio_output_dir,
                audio_format='wav',
                sample_rate=16000,  # Whisper recommended sample rate
                channels=1          # Mono, reduce file size
            )

            temp_audio_path = Path(audio_file_to_process)
            print(f"Video conversion completed: {temp_audio_path.name}")

        elif converter.is_audio_file(media_path):
            print(f"Detected audio file: {media_path.name}")
            audio_file_to_process = str(media_path)
        else:
            raise ValueError(f"Unsupported file format: {media_path.suffix}")

        # Prepare request
        url = f"{server_url}/transcribe"

        # Prepare form data
        data = {
            "language": language,
            "output_format": output_format,
            "task": task,
        }

        if initial_prompt:
            data["initial_prompt"] = initial_prompt

        # Prepare file
        audio_path = Path(audio_file_to_process)
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/*")}

            # Send request
            print(f"Sending request to {url}...")
            print(f"Processing file: {audio_path.name}")
            print(f"Language: {language}, Format: {output_format}")

            response = requests.post(url, data=data, files=files)

        # Check response
        if response.status_code == 200:
            result = response.json()['content']
            detected_language = response.json()['language']
            print("Transcription successful!")

            # Convert Chinese format if specified
            if detected_language == "zh":
                if CHINESE_CONVERSION_AVAILABLE:
                    print(f"Converting Chinese text to {chinese_format}...")
                    result = convert_chinese_text(result, chinese_format)
                else:
                    print(
                        "Warning: Chinese conversion not available. Skipping conversion.")

            # Save results
            saved_srt_path = None
            if save_path:
                save_file = Path(save_path)
                # Ensure save directory exists
                save_file.parent.mkdir(parents=True, exist_ok=True)
                save_file.write_text(result, encoding="utf-8")
                print(f"Results saved to: {save_path}")
                if output_format.lower() == "srt":
                    saved_srt_path = str(save_file)
            else:
                # If no save path specified but output directory is specified, auto-generate save path
                if output_dir:
                    output_path = Path(output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)
                    save_filename = f"{media_path.stem}.{output_format}"
                    auto_save_path = output_path / save_filename
                    auto_save_path.write_text(result, encoding="utf-8")
                    print(f"Results auto-saved to: {auto_save_path}")
                    if output_format.lower() == "srt":
                        saved_srt_path = str(auto_save_path)

            # If output format is SRT, also generate TXT version
            if output_format.lower() == "srt" and saved_srt_path:
                try:
                    txt_path = convert_srt_file_to_txt(saved_srt_path)
                    print(f"Additional TXT file generated: {txt_path}")
                except Exception as e:
                    print(
                        f"Warning: Failed to generate TXT file from SRT: {e}")

            return result
        else:
            error_msg = f"Request failed (status code: {response.status_code}): {response.text}"
            print(error_msg)
            raise Exception(error_msg)

    finally:
        # Clean up temporary files
        if temp_audio_path and temp_audio_path.exists() and not keep_temp_audio:
            try:
                os.unlink(temp_audio_path)
                print(f"Cleaned up temporary file: {temp_audio_path.name}")
            except Exception as e:
                print(f"Failed to clean up temporary file: {e}")


def check_output_exists(media_file_path: str, output_dir: str, output_format: str) -> bool:
    """
    Check if output file already exists for the given media file

    Args:
        media_file_path: Path to the media file
        output_dir: Output directory
        output_format: Output format (srt, txt, etc.)

    Returns:
        True if output file exists, False otherwise
    """
    media_path = Path(media_file_path)
    output_path = Path(output_dir)

    # Check main output file
    main_output_file = output_path / f"{media_path.stem}.{output_format}"
    if main_output_file.exists():
        return True

    # If main format is SRT, also check for TXT file
    if output_format.lower() == "srt":
        txt_output_file = output_path / f"{media_path.stem}.txt"
        if txt_output_file.exists():
            return True

    return False


def batch_transcribe_media(
    input_dir: str,
    server_url: str = whisper_api_url,
    language: str = "zh",
    output_format: str = "srt",
    task: str = "transcribe",
    initial_prompt: str = None,
    output_dir: str = None,
    keep_temp_audio: bool = False,
    chinese_format: str = "simplified",
    skip_existing: bool = True,
    file_patterns: list = None
):
    """
    Batch transcribe all media files in a directory

    Args:
        input_dir: Directory containing media files
        server_url: Whisper server URL
        language: Language code
        output_format: Output format
        task: Task type
        initial_prompt: Initial prompt text
        output_dir: Output directory (defaults to ./whisper_output)
        keep_temp_audio: Whether to keep temporary audio files
        chinese_format: Chinese character format
        skip_existing: Whether to skip files that already have output
        file_patterns: List of file patterns to process (defaults to common media formats)

    Returns:
        Dictionary with processing results
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    # Set default output directory to project root whisper_output
    if output_dir is None:
        # Use the current working directory (project root) + whisper_output
        output_dir = "whisper_output"

    # Set default file patterns for media files
    if file_patterns is None:
        file_patterns = [
            "*.mp4", "*.avi", "*.mkv", "*.mov", "*.wmv", "*.flv", "*.webm",  # Video
            "*.mp3", "*.wav", "*.flac", "*.aac", "*.ogg", "*.m4a", "*.wma"   # Audio
        ]

    # Find all media files
    media_files = []
    for pattern in file_patterns:
        media_files.extend(input_path.glob(pattern))
        # Also search in subdirectories
        media_files.extend(input_path.rglob(pattern))

    # Remove duplicates and sort
    media_files = sorted(list(set(media_files)))

    if not media_files:
        print(f"No media files found in {input_dir}")
        print(f"Searched for patterns: {file_patterns}")
        return {"processed": 0, "skipped": 0, "failed": 0, "results": []}

    print(f"Found {len(media_files)} media files to process")
    print(f"Output directory: {output_dir}")
    print(f"Skip existing: {skip_existing}")
    print("-" * 60)

    results = {
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "results": []
    }

    # Initialize converter for file type checking
    converter = VideoConverter()

    for i, media_file in enumerate(media_files, 1):
        print(f"\n[{i}/{len(media_files)}] Processing: {media_file.name}")

        # Check if file is actually a media file
        if not (converter.is_video_file(media_file) or converter.is_audio_file(media_file)):
            print(f"  ⚠️  Skipping non-media file: {media_file.name}")
            results["skipped"] += 1
            continue

        # Check if output already exists
        if skip_existing and check_output_exists(str(media_file), output_dir, output_format):
            print(f"  ✓  Output already exists, skipping: {media_file.name}")
            results["skipped"] += 1
            results["results"].append({
                "file": str(media_file),
                "status": "skipped",
                "reason": "output_exists"
            })
            continue

        try:
            # Process the file
            print(f"  🔄 Transcribing: {media_file.name}")
            result = transcribe_media(
                media_file_path=str(media_file),
                server_url=server_url,
                language=language,
                output_format=output_format,
                task=task,
                initial_prompt=initial_prompt,
                save_path=None,  # Use auto-generated path
                output_dir=output_dir,
                keep_temp_audio=keep_temp_audio,
                chinese_format=chinese_format
            )

            print(f"  ✅ Successfully processed: {media_file.name}")
            results["processed"] += 1
            results["results"].append({
                "file": str(media_file),
                "status": "success",
                "output_length": len(result)
            })

        except Exception as e:
            print(f"  ❌ Failed to process {media_file.name}: {str(e)}")
            results["failed"] += 1
            results["results"].append({
                "file": str(media_file),
                "status": "failed",
                "error": str(e)
            })

    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total files found: {len(media_files)}")
    print(f"Successfully processed: {results['processed']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Failed: {results['failed']}")
    print(f"Output directory: {output_dir}")

    return results


def check_server_health(server_url: str = whisper_api_url):
    """
    Check server health status

    Args:
        server_url: Server URL

    Returns:
        Server status information
    """
    url = f"{server_url}/health"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Cannot connect to server: {response.status_code}")


def main():
    """Main function - example usage"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Whisper client - Single file or batch processing")
    parser.add_argument("input_path", type=str,
                        help="Media file path or directory (auto-detects batch mode for directories)")
    parser.add_argument(
        "--server",
        type=str,
        default=whisper_api_url,
        help="Whisper server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="srt",
        choices=["srt", "txt", "vtt", "tsv", "json"],
        help="Output format (default: srt)"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="transcribe",
        choices=["transcribe", "translate"],
        help="Task type (default: transcribe)"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Initial prompt text"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (only for single file processing)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: ./whisper_output)"
    )
    parser.add_argument(
        "--chinese-format",
        type=str,
        default="simplified",
        choices=["simplified", "traditional"],
        help="Chinese character format (simplified/traditional)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Force batch processing mode (auto-enabled for directories)"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Process files even if output already exists (default: skip existing)"
    )
    parser.add_argument(
        "--file-patterns",
        nargs="*",
        default=None,
        help="File patterns to match in batch mode (e.g., *.mp4 *.wav)"
    )

    args = parser.parse_args()

    try:
        # Check server status
        print("Checking server status...")
        health = check_server_health(args.server)
        print(f"Server status: {health}")
        print()

        input_path = Path(args.input_path)

        # Auto-detect batch processing mode
        # If input is a directory, enable batch mode automatically
        # If --batch flag is explicitly set, also enable batch mode
        is_batch = input_path.is_dir() or args.batch

        if is_batch:
            # Batch processing mode
            if not input_path.is_dir():
                print(
                    f"Error: Batch mode requires a directory, got: {args.input_path}")
                return 1

            if args.output:
                print("Warning: --output option is ignored in batch mode")

            batch_reason = "auto-detected (directory input)" if input_path.is_dir(
            ) and not args.batch else "explicitly enabled"
            print(f"BATCH PROCESSING MODE ({batch_reason})")
            print(f"Input directory: {input_path}")

            results = batch_transcribe_media(
                input_dir=str(input_path),
                server_url=args.server,
                language=args.language,
                output_format=args.format,
                task=args.task,
                initial_prompt=args.prompt,
                output_dir=args.output_dir,
                keep_temp_audio=False,
                chinese_format=args.chinese_format,
                skip_existing=not args.no_skip_existing,
                file_patterns=args.file_patterns
            )

            # Return non-zero exit code if any files failed
            return 1 if results["failed"] > 0 else 0

        else:
            # Single file processing mode
            if not input_path.exists():
                print(f"Error: Input file does not exist: {args.input_path}")
                return 1

            if input_path.is_dir():
                print(
                    "Error: Input is a directory. Use --batch flag for batch processing")
                return 1

            print(f"SINGLE FILE PROCESSING MODE")
            print(f"Input file: {input_path}")

            # Process output path and output directory
            output_path = args.output
            output_dir = args.output_dir or "whisper_output"  # Default output directory

            if not output_path and not args.output_dir:
                # If neither specified, use default output directory and auto-generated filename
                output_path = Path(output_dir) / \
                    f"{input_path.stem}.{args.format}"

            # Check if output already exists and warn user
            if not args.no_skip_existing:
                if output_path and Path(output_path).exists():
                    print(
                        f"Warning: Output file already exists: {output_path}")
                    response = input("Continue anyway? (y/N): ")
                    if response.lower() != 'y':
                        print("Operation cancelled by user")
                        return 0

            # Transcribe media file
            result = transcribe_media(
                media_file_path=str(input_path),
                server_url=args.server,
                language=args.language,
                output_format=args.format,
                task=args.task,
                initial_prompt=args.prompt,
                save_path=output_path,
                output_dir=output_dir,
                chinese_format=args.chinese_format
            )

            print(f"\n✅ Processing completed successfully!")
            return 0

    except KeyboardInterrupt:
        print("\n\n❌ Processing interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


# Backward compatibility function

def transcribe_audio(audio_file_path: str, **kwargs):
    """
    Backward compatibility function: Transcribe audio file

    Args:
        audio_file_path: Audio file path
        **kwargs: Other parameters passed to transcribe_media

    Returns:
        Transcription result text
    """
    return transcribe_media(audio_file_path, **kwargs)


if __name__ == "__main__":
    exit(main())
