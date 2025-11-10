"""
批量处理示例 - Video2MD 工具包

演示如何批量处理多个文件
"""

from src.utils import ChineseConverter
from src.tools import WhisperTool, VideoConverterTool
import os
from pathlib import Path
import sys
import time

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def batch_video_conversion_example():
    """批量视频转音频示例"""
    print("=== 批量视频转音频示例 ===")

    converter = VideoConverterTool()

    # 检查输入目录
    input_dir = Path("input")
    if not input_dir.exists():
        print("📁 创建 input 目录")
        input_dir.mkdir()
        print("请将视频文件放入 input 目录中")
        return

    print(f"🔍 扫描目录: {input_dir}")

    try:
        # 执行批量转换
        results = converter.batch_convert_videos(
            input_dir=str(input_dir),
            output_dir="batch_audio_output",
            audio_format="wav",
            sample_rate=16000,
            channels=1,
            overwrite=False
        )

        # 显示结果
        print(f"\\n📊 批量转换完成:")
        print(f"  总文件数: {results['total']}")
        print(f"  转换成功: {results['converted']}")
        print(f"  跳过文件: {results['skipped']}")
        print(f"  转换失败: {results['failed']}")

        # 显示详细结果
        if results['results']:
            print("\\n📋 详细结果:")
            for result in results['results'][:5]:  # 只显示前5个
                status = result['status']
                input_file = Path(result['input']).name

                if status == 'success':
                    output_file = Path(result['output']).name
                    print(f"  ✅ {input_file} -> {output_file}")
                elif status == 'skipped':
                    print(f"  ⏭️ {input_file} (已存在)")
                else:
                    error = result.get('error', '未知错误')
                    print(f"  ❌ {input_file}: {error}")

    except Exception as e:
        print(f"❌ 批量转换失败: {e}")


def batch_transcription_example():
    """批量转录示例"""
    print("\\n=== 批量转录示例 ===")

    whisper = WhisperTool()

    # 检查服务器状态
    try:
        health = whisper.check_server_health()
        print(f"✅ Whisper 服务器状态正常")
    except Exception as e:
        print(f"❌ Whisper 服务器不可用: {e}")
        print("跳过转录示例")
        return

    # 检查输入目录
    input_dir = Path("input")
    if not input_dir.exists() or not any(input_dir.iterdir()):
        print("📁 input 目录为空，跳过批量转录")
        return

    print(f"🔍 扫描媒体文件: {input_dir}")

    try:
        # 执行批量转录
        results = whisper.batch_transcribe(
            input_dir=str(input_dir),
            language="zh",
            output_format="srt",
            output_dir="batch_transcripts",
            chinese_format="simplified",
            skip_existing=True
        )

        # 显示结果
        print(f"\\n📊 批量转录完成:")
        print(f"  总文件数: {results['total']}")
        print(f"  转录成功: {results['processed']}")
        print(f"  跳过文件: {results['skipped']}")
        print(f"  转录失败: {results['failed']}")

        # 显示成功的转录
        success_results = [r for r in results['results']
                           if r.get('status') == 'success']
        if success_results:
            print("\\n📋 转录结果:")
            for result in success_results[:3]:  # 只显示前3个
                input_file = Path(result['input_file']).name
                saved_files = result.get('saved_files', [])
                print(f"  ✅ {input_file}")
                for saved_file in saved_files:
                    print(f"    -> {Path(saved_file).name}")

    except Exception as e:
        print(f"❌ 批量转录失败: {e}")


def batch_chinese_conversion_example():
    """批量中文转换示例"""
    print("\\n=== 批量中文转换示例 ===")

    converter = ChineseConverter()

    if not converter.is_available():
        print("❌ 中文转换功能不可用，请安装 zhconv")
        return

    # 创建测试文件
    test_dir = Path("test_chinese_files")
    test_dir.mkdir(exist_ok=True)

    # 创建一些测试文件
    test_files = {
        "simplified.txt": "这是简体中文测试文件。包含一些文本内容。",
        "traditional.txt": "這是繁體中文測試檔案。包含一些文字內容。",
        "mixed.srt": """1
00:00:01,000 --> 00:00:03,000
这是简体字幕

2
00:00:04,000 --> 00:00:06,000
這是繁體字幕
"""
    }

    print("📝 创建测试文件...")
    for filename, content in test_files.items():
        file_path = test_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  创建: {filename}")

    try:
        # 批量转换为简体
        print("\\n🔄 批量转换为简体中文...")
        results = converter.batch_convert_files(
            input_dir=str(test_dir),
            target_format="simplified",
            output_dir="chinese_output/simplified"
        )

        print(f"转换结果: 成功 {results['converted']}, 失败 {results['failed']}")

        # 批量转换为繁体
        print("\\n🔄 批量转换为繁体中文...")
        results = converter.batch_convert_files(
            input_dir=str(test_dir),
            target_format="traditional",
            output_dir="chinese_output/traditional"
        )

        print(f"转换结果: 成功 {results['converted']}, 失败 {results['failed']}")

        # 显示转换结果
        output_dir = Path("chinese_output")
        if output_dir.exists():
            print("\\n📄 输出文件:")
            for file_path in output_dir.rglob("*.txt"):
                print(f"  {file_path}")

    except Exception as e:
        print(f"❌ 批量中文转换失败: {e}")


def performance_monitoring_example():
    """性能监控示例"""
    print("\\n=== 性能监控示例 ===")

    from src.lib.file_utils import get_file_size_human, find_files

    # 统计项目文件
    print("📊 项目文件统计:")

    # Python 文件
    python_files = find_files("src", ["*.py"], recursive=True)
    print(f"  Python 文件: {len(python_files)} 个")

    # 媒体文件
    media_patterns = ["*.mp4", "*.mp3", "*.wav", "*.avi", "*.mkv"]
    media_files = find_files(".", media_patterns, recursive=True)
    print(f"  媒体文件: {len(media_files)} 个")

    # 输出文件
    output_patterns = ["*.srt", "*.txt"]
    output_files = find_files(".", output_patterns, recursive=True)
    print(f"  输出文件: {len(output_files)} 个")

    # 计算总大小
    total_size = 0
    for file_list in [python_files, media_files, output_files]:
        for file_path in file_list:
            try:
                size = file_path.stat().st_size
                total_size += size
            except:
                pass

    print(f"  总文件大小: {get_file_size_human(Path('/tmp/dummy_file'))} (估算)")

    # 性能测试
    print("\\n⏱️ 性能测试:")

    # 测试文件操作速度
    start_time = time.time()
    test_files = find_files(".", ["*.*"], recursive=True)
    end_time = time.time()

    print(f"  文件扫描: {len(test_files)} 个文件, 耗时 {end_time - start_time:.2f} 秒")


def main():
    """运行所有批量处理示例"""
    print("🚀 Video2MD 工具包 - 批量处理示例\\n")

    # 设置环境变量
    if not os.getenv("WHISPER_API_URL"):
        os.environ["WHISPER_API_URL"] = "http://localhost:8000"

    try:
        batch_video_conversion_example()
        batch_chinese_conversion_example()
        performance_monitoring_example()
        batch_transcription_example()  # 放在最后，因为需要服务器

    except KeyboardInterrupt:
        print("\\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"\\n❌ 运行示例时发生错误: {e}")
        import traceback
        traceback.print_exc()

    print("\\n✨ 批量处理示例运行完成！")


if __name__ == "__main__":
    main()
