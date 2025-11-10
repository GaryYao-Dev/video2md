"""
基本使用示例 - Video2MD 工具包

演示如何使用各种工具进行媒体处理和转录
"""

from src.utils import ChineseConverter
from src.tools import WhisperTool, VideoConverterTool
import os
from pathlib import Path
import sys

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def example_whisper_transcription():
    """演示 Whisper 转录功能"""
    print("=== Whisper 转录示例 ===")

    whisper = WhisperTool()

    # 检查服务器状态
    try:
        health = whisper.check_server_health()
        print(f"✅ Whisper 服务器状态: {health}")
    except Exception as e:
        print(f"❌ Whisper 服务器不可用: {e}")
        return

    # 查找测试文件
    input_dir = Path("input")
    if not input_dir.exists():
        print("📁 创建 input 目录，请放入测试媒体文件")
        input_dir.mkdir()
        return

    # 寻找媒体文件
    media_files = []
    for ext in ['.mp4', '.mp3', '.wav', '.avi']:
        media_files.extend(input_dir.glob(f"*{ext}"))

    if not media_files:
        print("📁 input 目录中没有找到媒体文件")
        return

    # 转录第一个找到的文件
    test_file = media_files[0]
    print(f"🎬 转录文件: {test_file.name}")

    try:
        result = whisper.transcribe_single_file(
            media_file_path=str(test_file),
            language="zh",
            output_format="srt",
            output_dir="whisper_output",
            chinese_format="simplified"
        )

        print(f"✅ 转录成功!")
        print(f"📄 输出文件: {result['saved_files']}")
        print(f"📝 转录内容预览: {result['transcription'][:200]}...")

    except Exception as e:
        print(f"❌ 转录失败: {e}")


def example_video_conversion():
    """演示视频转音频功能"""
    print("\\n=== 视频转音频示例 ===")

    converter = VideoConverterTool()

    # 查找视频文件
    input_dir = Path("input")
    if not input_dir.exists():
        print("📁 input 目录不存在")
        return

    video_files = []
    for ext in converter.SUPPORTED_VIDEO_FORMATS:
        video_files.extend(input_dir.glob(f"*{ext}"))

    if not video_files:
        print("📁 input 目录中没有找到视频文件")
        return

    # 转换第一个视频文件
    test_video = video_files[0]
    print(f"🎥 转换视频: {test_video.name}")

    try:
        audio_path = converter.convert_video_to_audio(
            input_path=str(test_video),
            output_dir="audio_output",
            audio_format="wav",
            sample_rate=16000,
            channels=1
        )

        print(f"✅ 转换成功!")
        print(f"🎵 音频文件: {audio_path}")

        # 显示文件信息
        from src.lib.file_utils import get_file_size_human
        size = get_file_size_human(audio_path)
        print(f"📊 文件大小: {size}")

    except Exception as e:
        print(f"❌ 转换失败: {e}")


def example_chinese_conversion():
    """演示中文文本转换功能"""
    print("\\n=== 中文文本转换示例 ===")

    converter = ChineseConverter()

    if not converter.is_available():
        print("❌ 中文转换功能不可用，请安装 zhconv: pip install zhconv")
        return

    # 文本转换示例
    test_texts = [
        "这是简体中文测试文本",
        "這是繁體中文測試文本",
        "混合簡體和繁体文本"
    ]

    for text in test_texts:
        print(f"\\n原文: {text}")

        # 转为简体
        simplified = converter.convert_text(text, "simplified")
        print(f"简体: {simplified}")

        # 转为繁体
        traditional = converter.convert_text(text, "traditional")
        print(f"繁體: {traditional}")

        # 检测类型
        detection = converter.detect_chinese_type(text)
        if detection.get('available'):
            print(f"检测类型: {detection.get('detected_type', '未知')}")


def example_file_operations():
    """演示文件操作功能"""
    print("\\n=== 文件操作示例 ===")

    from src.lib.file_utils import (
        ensure_dir_exists,
        get_file_size_human,
        find_files,
        clean_filename
    )

    # 确保目录存在
    test_dir = ensure_dir_exists("test_output")
    print(f"📁 创建/确认目录: {test_dir}")

    # 查找文件
    media_files = find_files(".", ["*.mp4", "*.mp3", "*.wav"], recursive=True)
    print(f"🔍 找到 {len(media_files)} 个媒体文件")

    # 显示文件信息
    for file in media_files[:3]:  # 只显示前3个
        try:
            size = get_file_size_human(file)
            print(f"  📄 {file.name}: {size}")
        except:
            pass

    # 文件名清理示例
    dirty_names = ["文件<名>称.mp4", "test|file?.wav", "name:with*chars.txt"]
    print("\\n🧹 文件名清理:")
    for name in dirty_names:
        clean = clean_filename(name)
        print(f"  {name} -> {clean}")


def main():
    """运行所有示例"""
    print("🚀 Video2MD 工具包 - 基本使用示例\\n")

    # 设置环境变量（如果需要）
    if not os.getenv("WHISPER_API_URL"):
        os.environ["WHISPER_API_URL"] = "http://localhost:8000"

    try:
        example_video_conversion()
        example_chinese_conversion()
        example_file_operations()
        example_whisper_transcription()  # 放在最后，因为需要服务器

    except KeyboardInterrupt:
        print("\\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"\\n❌ 运行示例时发生错误: {e}")

    print("\\n✨ 示例运行完成！")


if __name__ == "__main__":
    main()
