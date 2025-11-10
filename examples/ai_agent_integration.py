"""
AI Agent 集成示例 - Video2MD 工具包

演示如何将工具集成到 AI Agent 中使用
"""

from video2md.clients.whisper_client import (
    check_server_health,
    batch_transcribe_media,
    transcribe_media,
)  # type: ignore
from video2md.utils.chinese_converter import convert_file as cn_convert_file  # type: ignore
from video2md.utils.video_converter import VideoConverter  # type: ignore
import os
from pathlib import Path
import sys
import json
from typing import Dict, List, Any

# 确保 src/ 在 Python 路径中（源代码运行场景）
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# 引入打包后的工具模块


def find_files(directory: str, patterns: List[str], recursive: bool = True) -> List[Path]:
    """按通配符在目录中查找文件"""
    base = Path(directory)
    files: List[Path] = []
    for pat in patterns:
        if recursive:
            files.extend(base.rglob(pat))
        else:
            files.extend(base.glob(pat))
    # 去重并排序
    return sorted(list(set(files)))


class VideoConverterTool:
    """视频转换封装（基于打包模块）"""

    SUPPORTED_VIDEO_FORMATS = VideoConverter.SUPPORTED_VIDEO_FORMATS
    SUPPORTED_AUDIO_FORMATS = VideoConverter.SUPPORTED_AUDIO_FORMATS

    def __init__(self) -> None:
        self._conv = VideoConverter()

    def _check_ffmpeg(self) -> None:
        # 构造函数已校验 ffmpeg，可再次触发以抛出错误
        self._conv._check_ffmpeg()

    def is_video_file(self, p: Path) -> bool:
        return self._conv.is_video_file(p)

    def convert_video_to_audio(self, input_path: str | Path, output_dir: str | Path, audio_format: str = "wav") -> str:
        return self._conv.video_to_audio(input_path=input_path, output_dir=output_dir, audio_format=audio_format)

    def batch_convert_videos(self, input_dir: str, output_dir: str, audio_format: str = "wav") -> Dict[str, Any]:
        video_patterns = [f"*{ext}" for ext in self.SUPPORTED_VIDEO_FORMATS]
        video_files = find_files(input_dir, video_patterns)
        results: Dict[str, Any] = {"converted": 0, "failed": 0, "results": []}
        for vf in video_files:
            try:
                out = self.convert_video_to_audio(vf, output_dir, audio_format)
                results["converted"] += 1
                results["results"].append({"input": str(vf), "output": out})
            except Exception as e:
                results["failed"] += 1
                results["results"].append({"input": str(vf), "error": str(e)})
        return results


class WhisperTool:
    """Whisper 客户端封装（基于打包模块）"""

    def __init__(self, whisper_url: str = "http://localhost:8000") -> None:
        self.url = whisper_url

    def check_server_health(self) -> Dict[str, Any]:
        return check_server_health(self.url)

    def batch_transcribe(self, input_dir: str, output_dir: str, language: str = "zh", chinese_format: str = "simplified") -> Dict[str, Any]:
        return batch_transcribe_media(
            input_dir=input_dir,
            server_url=self.url,
            language=language,
            output_format="srt",
            task="transcribe",
            initial_prompt=None,
            output_dir=output_dir,
            keep_temp_audio=False,
            chinese_format=chinese_format,
            skip_existing=True,
            file_patterns=None,
        )

    def transcribe_single_file(self, media_file_path: str, output_dir: str, language: str = "zh", chinese_format: str = "simplified") -> Dict[str, Any]:
        # 使用打包函数执行转录；自动保存到 output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        _ = transcribe_media(
            media_file_path=media_file_path,
            server_url=self.url,
            language=language,
            output_format="srt",
            task="transcribe",
            initial_prompt=None,
            save_path=None,
            output_dir=output_dir,
            keep_temp_audio=False,
            chinese_format=chinese_format,
        )
        stem = Path(media_file_path).stem
        srt_path = str(Path(output_dir) / f"{stem}.srt")
        txt_path = str(Path(output_dir) / f"{stem}.txt")
        return {"saved_files": [p for p in [srt_path, txt_path] if Path(p).exists()]}


class ChineseConverter:
    """中文繁简转换封装（基于打包模块）"""

    def __init__(self) -> None:
        try:
            import zhconv  # noqa: F401
            self._available = True
        except Exception:
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def convert_file(self, input_file: str, target_format: str = "simplified", output_file: str | None = None) -> str:
        return cn_convert_file(input_file=input_file, output_file=output_file, target_format=target_format)

    def batch_convert_files(self, input_dir: str, target_format: str = "simplified", output_dir: str | None = None) -> Dict[str, Any]:
        files = find_files(
            input_dir, ["*.srt", "*.txt", "*.vtt"], recursive=True)
        results: Dict[str, Any] = {"converted": 0, "failed": 0, "results": []}
        Path(output_dir or input_dir).mkdir(parents=True, exist_ok=True)
        for fp in files:
            try:
                out = None
                if output_dir:
                    out = str(Path(output_dir) / fp.name)
                outp = self.convert_file(
                    str(fp), target_format=target_format, output_file=out)
                results["converted"] += 1
                results["results"].append({"input": str(fp), "output": outp})
            except Exception as e:
                results["failed"] += 1
                results["results"].append({"input": str(fp), "error": str(e)})
        return results


class MediaProcessingAgent:
    """
    媒体处理 AI Agent：集成 Whisper 转录、视频转换、中文处理等功能
    """

    def __init__(self, whisper_url: str = "http://localhost:8000"):
        self.whisper = WhisperTool(whisper_url)
        self.video_converter = VideoConverterTool()
        self.chinese_converter = ChineseConverter()

        # Agent 状态
        self.status = {
            "whisper_available": False,
            "ffmpeg_available": False,
            "chinese_converter_available": False,
        }

        self._check_dependencies()

    def _check_dependencies(self) -> None:
        # 检查 Whisper 服务器
        try:
            self.whisper.check_server_health()
            self.status["whisper_available"] = True
        except Exception:
            self.status["whisper_available"] = False

        # 检查 FFmpeg
        try:
            self.video_converter._check_ffmpeg()
            self.status["ffmpeg_available"] = True
        except Exception:
            self.status["ffmpeg_available"] = False

        # 检查中文转换器
        self.status["chinese_converter_available"] = self.chinese_converter.is_available()

    def get_agent_status(self) -> Dict[str, Any]:
        return {
            "agent_name": "MediaProcessingAgent",
            "version": "1.0.0",
            "status": self.status,
            "supported_video_formats": list(self.video_converter.SUPPORTED_VIDEO_FORMATS),
            "supported_audio_formats": list(self.video_converter.SUPPORTED_AUDIO_FORMATS),
            "capabilities": [
                "video_to_audio_conversion",
                "audio_transcription",
                "chinese_text_conversion",
                "batch_processing",
                "file_management",
            ],
        }

    def analyze_media_directory(self, directory: str) -> Dict[str, Any]:
        dir_path = Path(directory)
        if not dir_path.exists():
            return {"error": f"Directory not found: {directory}"}

        video_files = find_files(
            directory, [f"*{ext}" for ext in self.video_converter.SUPPORTED_VIDEO_FORMATS])
        audio_files = find_files(
            directory, [f"*{ext}" for ext in self.video_converter.SUPPORTED_AUDIO_FORMATS])
        subtitle_files = find_files(directory, ["*.srt", "*.vtt", "*.txt"])

        def get_total_size(file_list: List[Path]) -> int:
            total = 0
            for file_path in file_list:
                try:
                    total += file_path.stat().st_size
                except Exception:
                    pass
            return total

        analysis = {
            "directory": str(dir_path),
            "video_files": {"count": len(video_files), "files": [str(f) for f in video_files], "total_size": get_total_size(video_files)},
            "audio_files": {"count": len(audio_files), "files": [str(f) for f in audio_files], "total_size": get_total_size(audio_files)},
            "subtitle_files": {"count": len(subtitle_files), "files": [str(f) for f in subtitle_files]},
            "recommendations": [],
        }

        if analysis["video_files"]["count"] > 0:
            analysis["recommendations"].append({
                "action": "convert_videos",
                "description": f"Convert {analysis['video_files']['count']} video files to audio",
                "estimated_time": f"{analysis['video_files']['count'] * 2} minutes",
            })

        if analysis["audio_files"]["count"] > 0 and self.status["whisper_available"]:
            analysis["recommendations"].append({
                "action": "transcribe_audio",
                "description": f"Transcribe {analysis['audio_files']['count']} audio files",
                "estimated_time": f"{analysis['audio_files']['count'] * 3} minutes",
            })

        if analysis["subtitle_files"]["count"] > 0 and self.status["chinese_converter_available"]:
            analysis["recommendations"].append({
                "action": "convert_chinese",
                "description": f"Convert Chinese text in {analysis['subtitle_files']['count']} files",
                "estimated_time": "1 minute",
            })

        return analysis

    def execute_media_pipeline(self, input_directory: str, output_directory: str = "agent_output", language: str = "zh", chinese_format: str = "simplified") -> Dict[str, Any]:
        pipeline_results: Dict[str, Any] = {
            "input_directory": input_directory,
            "output_directory": output_directory,
            "steps": [],
            "total_files_processed": 0,
            "errors": [],
        }

        output_path = Path(output_directory)
        output_path.mkdir(exist_ok=True)

        try:
            print("🔍 Step 1: Analyzing input directory...")
            analysis = self.analyze_media_directory(input_directory)
            pipeline_results["steps"].append(
                {"step": "analyze_directory", "status": "completed", "result": analysis})

            if analysis["video_files"]["count"] > 0 and self.status["ffmpeg_available"]:
                print(
                    f"🎥 Step 2: Converting {analysis['video_files']['count']} videos to audio...")
                video_output_dir = output_path / "audio"
                conversion_results = self.video_converter.batch_convert_videos(
                    input_dir=input_directory, output_dir=str(video_output_dir), audio_format="wav"
                )
                pipeline_results["steps"].append(
                    {"step": "video_to_audio", "status": "completed", "result": conversion_results})
                pipeline_results["total_files_processed"] += conversion_results["converted"]

            if self.status["whisper_available"]:
                print("🎙️ Step 3: Transcribing audio files...")
                transcription_dirs = [input_directory]
                if (output_path / "audio").exists():
                    transcription_dirs.append(str(output_path / "audio"))

                all_transcription_results = {"processed": 0, "results": []}
                for trans_dir in transcription_dirs:
                    transcription_results = self.whisper.batch_transcribe(
                        input_dir=trans_dir,
                        output_dir=str(output_path / "transcripts"),
                        language=language,
                        chinese_format=chinese_format,
                    )
                    all_transcription_results["processed"] += transcription_results["processed"]
                    all_transcription_results["results"].extend(
                        transcription_results["results"])

                pipeline_results["steps"].append(
                    {"step": "audio_transcription", "status": "completed", "result": all_transcription_results})
                pipeline_results["total_files_processed"] += all_transcription_results["processed"]

            if self.status["chinese_converter_available"]:
                print("🇨🇳 Step 4: Converting Chinese text format...")
                transcript_dir = output_path / "transcripts"
                if transcript_dir.exists():
                    chinese_results = self.chinese_converter.batch_convert_files(
                        input_dir=str(transcript_dir), target_format=chinese_format, output_dir=str(output_path / f"chinese_{chinese_format}")
                    )
                    pipeline_results["steps"].append(
                        {"step": "chinese_conversion", "status": "completed", "result": chinese_results})
                    pipeline_results["total_files_processed"] += chinese_results["converted"]

            print("✅ Pipeline completed successfully!")
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            pipeline_results["errors"].append(error_msg)
            print(f"❌ {error_msg}")
        return pipeline_results

    def process_single_media_file(self, file_path: str, output_dir: str = "single_output", include_transcription: bool = True, include_chinese_conversion: bool = True, language: str = "zh", chinese_format: str = "simplified") -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

        results: Dict[str, Any] = {"input_file": str(
            file_path), "output_directory": output_dir, "steps_completed": [], "output_files": [], "errors": []}
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        try:
            current_file = str(file_path)
            if self.video_converter.is_video_file(file_path):
                print(f"🎥 Converting video to audio: {file_path.name}")
                audio_file = self.video_converter.convert_video_to_audio(
                    input_path=current_file, output_dir=str(output_path), audio_format="wav")
                results["steps_completed"].append("video_to_audio")
                results["output_files"].append(audio_file)
                current_file = audio_file

            if include_transcription and self.status["whisper_available"]:
                print(f"🎙️ Transcribing audio: {Path(current_file).name}")
                transcription_result = self.whisper.transcribe_single_file(
                    media_file_path=current_file, output_dir=str(output_path), language=language, chinese_format=chinese_format
                )
                results["steps_completed"].append("transcription")
                results["output_files"].extend(
                    transcription_result.get("saved_files", []))

            if include_chinese_conversion and self.status["chinese_converter_available"]:
                subtitle_files = find_files(
                    str(output_path), ["*.srt", "*.txt"])
                if subtitle_files:
                    print(
                        f"🇨🇳 Converting Chinese format in {len(subtitle_files)} files")
                    for subtitle_file in subtitle_files:
                        try:
                            converted_file = self.chinese_converter.convert_file(
                                input_file=str(subtitle_file), target_format=chinese_format)
                            results["output_files"].append(converted_file)
                        except Exception as e:
                            results["errors"].append(
                                f"Chinese conversion error for {subtitle_file}: {e}")
                    results["steps_completed"].append("chinese_conversion")
        except Exception as e:
            results["errors"].append(f"Processing error: {str(e)}")
        return results


def agent_integration_demo():
    print("🤖 AI Agent 集成演示\n")
    agent = MediaProcessingAgent()
    status = agent.get_agent_status()
    print("📋 Agent 状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))

    test_dir = Path("agent_test_input")
    test_dir.mkdir(exist_ok=True)

    analysis = agent.analyze_media_directory(str(test_dir))
    print(f"\n🔍 目录分析结果:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))

    if analysis["video_files"]["count"] > 0 or analysis["audio_files"]["count"] > 0:
        print("\n🔄 执行媒体处理流水线...")
        pipeline_results = agent.execute_media_pipeline(
            input_directory=str(test_dir), output_directory="agent_pipeline_output", language="zh", chinese_format="simplified"
        )
        print("📊 流水线执行结果:")
        print(json.dumps(pipeline_results, indent=2, ensure_ascii=False))
    else:
        print("\n💡 提示：将媒体文件放入 'agent_test_input' 目录以测试完整流水线")
        media_files = find_files(
            ".", ["*.mp4", "*.mp3", "*.wav"], recursive=True)
        if media_files:
            test_file = media_files[0]
            print(f"\n🎯 演示单文件处理: {test_file.name}")
            single_result = agent.process_single_media_file(
                file_path=str(test_file), output_dir="agent_single_output", include_transcription=True, include_chinese_conversion=True
            )
            print("📋 单文件处理结果:")
            print(json.dumps(single_result, indent=2, ensure_ascii=False))


def main():
    print("🚀 Video2MD 工具包 - AI Agent 集成示例\n")
    if not os.getenv("WHISPER_API_URL"):
        os.environ["WHISPER_API_URL"] = "http://localhost:8000"
    try:
        agent_integration_demo()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 运行示例时发生错误: {e}")
        import traceback
        traceback.print_exc()
    print("\n✨ AI Agent 集成示例运行完成！")


if __name__ == "__main__":
    main()
