#!/usr/bin/env python3
"""
Chinese Text Converter Tool
Convert between Simplified and Traditional Chinese in text files
"""

import argparse
import sys
from pathlib import Path

# Import zhconv for Traditional/Simplified Chinese conversion
try:
    import zhconv
    ZHCONV_AVAILABLE = True
except ImportError:
    ZHCONV_AVAILABLE = False


def convert_chinese_text(text: str, target_format: str = "simplified") -> str:
    """
    Convert between Simplified and Traditional Chinese using zhconv

    Args:
        text: Input Chinese text
        target_format: "simplified" or "traditional"

    Returns:
        Converted text
    """
    if not ZHCONV_AVAILABLE:
        print("Error: zhconv not installed. Chinese conversion disabled.")
        print("To enable conversion, install zhconv: pip install zhconv")
        return text

    try:
        if target_format.lower() == "simplified":
            return zhconv.convert(text, 'zh-cn')
        elif target_format.lower() == "traditional":
            return zhconv.convert(text, 'zh-tw')
        else:
            print(
                f"Warning: Unknown target format '{target_format}'. Supported: 'simplified', 'traditional'")
            return text
    except Exception as e:
        print(f"Warning: Chinese conversion failed: {e}")
        return text


def convert_file(input_file: str, output_file: str = None, target_format: str = "simplified"):
    """
    Convert Chinese characters in a text file

    Args:
        input_file: Path to input file
        output_file: Path to output file (optional, defaults to input_file with suffix)
        target_format: "simplified" or "traditional"

    Returns:
        Path to output file
    """
    if not ZHCONV_AVAILABLE:
        print("Error: zhconv package is required for Chinese conversion.")
        print("Please install it with: pip install zhconv")
        sys.exit(1)

    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    # Read input file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print("Error: Failed to read file. Please ensure the file is UTF-8 encoded.")
        sys.exit(1)

    # Convert text
    converted_content = convert_chinese_text(content, target_format)

    # Determine output file path
    if output_file is None:
        suffix = "_simplified" if target_format == "simplified" else "_traditional"
        output_file = str(input_path.with_stem(input_path.stem + suffix))

    # Write output file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(converted_content)

    print(f"Converted {input_file} -> {output_file}")
    print(f"Format: {target_format} Chinese")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Convert between Simplified and Traditional Chinese in text files"
    )
    parser.add_argument(
        "input_file",
        help="Path to input text file (supports .txt, .srt, etc.)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (optional)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["simplified", "traditional"],
        default="simplified",
        help="Target Chinese format (default: simplified)"
    )
    parser.add_argument(
        "-b", "--batch",
        action="store_true",
        help="Process all .srt and .txt files in the input directory"
    )

    args = parser.parse_args()

    try:
        if args.batch:
            input_path = Path(args.input_file)
            if not input_path.is_dir():
                print("Error: For batch processing, input must be a directory")
                sys.exit(1)

            # Find all text files
            text_files = []
            for pattern in ["*.srt", "*.txt", "*.vtt"]:
                text_files.extend(input_path.glob(pattern))

            if not text_files:
                print("No text files found in the directory")
                sys.exit(1)

            print(f"Found {len(text_files)} text files to convert...")
            for file_path in text_files:
                try:
                    convert_file(str(file_path), target_format=args.format)
                except Exception as e:
                    print(f"Error converting {file_path}: {e}")
        else:
            convert_file(args.input_file, args.output, args.format)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
