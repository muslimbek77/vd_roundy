import asyncio
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


async def convert_video_to_video_note(bot: Bot, file_id: str) -> ConversionResult:
    temp_dir = Path(tempfile.mkdtemp(prefix="video_to_note_"))
    source_path = temp_dir / "source.mp4"
    result_path = temp_dir / "video_note.mp4"

    try:
        await bot.download(file=file_id, destination=source_path)
        await _run_ffmpeg(
            source_path,
            result_path,
            video_filter="crop=min(iw\\,ih):min(iw\\,ih),scale=640:640,setsar=1",
        )
        return ConversionResult(path=result_path, temp_dir=temp_dir)
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


async def _run_ffmpeg(source_path: Path, result_path: Path, video_filter: str) -> None:
    if shutil.which("ffmpeg") is None:
        raise ConversionError("ffmpeg is not installed")

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
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
