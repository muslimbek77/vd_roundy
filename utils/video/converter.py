import asyncio
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot


class ConversionError(Exception):
    """Raised when media conversion cannot be completed."""


@dataclass(slots=True)
class ConversionResult:
    path: Path
    temp_dir: Path


@dataclass(slots=True)
class VideoNoteBatchResult:
    paths: list[Path]
    temp_dir: Path


async def convert_video_to_video_note(
    bot: Bot,
    file_id: str,
    duration_seconds: int,
    max_total_duration: int = 180,
    chunk_duration: int = 60,
) -> VideoNoteBatchResult:
    temp_dir = Path(tempfile.mkdtemp(prefix="video_to_note_"))
    source_path = temp_dir / "source.mp4"

    try:
        await bot.download(file=file_id, destination=source_path)
        if duration_seconds <= 0:
            raise ConversionError("Video duration is not available")

        if duration_seconds > max_total_duration:
            raise ConversionError(
                f"Video duration too long: {duration_seconds}s. Max supported duration is {max_total_duration}s."
            )

        chunk_count = max(1, math.ceil(duration_seconds / chunk_duration))
        result_paths: list[Path] = []

        for index in range(chunk_count):
            start_seconds = index * chunk_duration
            current_duration = min(chunk_duration, duration_seconds - start_seconds)
            result_path = temp_dir / f"video_note_{index + 1}.mp4"
            await _run_ffmpeg(
                source_path,
                result_path,
                video_filter="crop=min(iw\\,ih):min(iw\\,ih),scale=640:640,setsar=1",
                start_seconds=start_seconds,
                duration_seconds=current_duration,
            )
            result_paths.append(result_path)

        return VideoNoteBatchResult(paths=result_paths, temp_dir=temp_dir)
    except Exception:
        cleanup_temp_dir(temp_dir)
        raise


async def convert_video_note_to_video(bot: Bot, file_id: str) -> ConversionResult:
    temp_dir = Path(tempfile.mkdtemp(prefix="note_to_video_"))
    source_path = temp_dir / "source.mp4"
    result_path = temp_dir / "video.mp4"

    try:
        await bot.download(file=file_id, destination=source_path)
        await _run_ffmpeg(
            source_path,
            result_path,
            video_filter=(
                "scale=720:720:force_original_aspect_ratio=decrease,"
                "pad=720:720:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
            ),
        )
        return ConversionResult(path=result_path, temp_dir=temp_dir)
    except Exception:
        cleanup_temp_dir(temp_dir)
        raise


def cleanup_temp_dir(temp_dir: Path) -> None:
    shutil.rmtree(temp_dir, ignore_errors=True)


async def _run_ffmpeg(
    source_path: Path,
    result_path: Path,
    video_filter: str,
    start_seconds: int = 0,
    duration_seconds: int | None = None,
) -> None:
    if shutil.which("ffmpeg") is None:
        raise ConversionError("ffmpeg is not installed")

    command = [
        "ffmpeg",
        "-y",
    ]

    if start_seconds > 0:
        command.extend(["-ss", str(start_seconds)])

    if duration_seconds is not None:
        command.extend(["-t", str(duration_seconds)])

    command.extend(
        [
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(result_path),
        ]
    )

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
    except asyncio.TimeoutError as error:
        process.kill()
        await process.communicate()
        raise ConversionError("Video processing timed out") from error

    if process.returncode != 0 or not result_path.exists():
        error_text = stderr.decode("utf-8", errors="ignore").strip()
        raise ConversionError(error_text or "ffmpeg video processing failed")
