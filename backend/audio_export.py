"""
Audio export module for generating downloadable audiobook files.
Supports: single MP3, MP3 per chapter (ZIP), and M4B (AAC with chapters).
"""
import io
import os
import struct
import subprocess
import tempfile
import zipfile
import logging
from typing import List, Optional, Tuple

from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3, TIT2, TPE1, TPE2, TALB, TCON, TDRC, COMM, TRCK, APIC
)
from mutagen.mp4 import MP4, MP4Cover

logger = logging.getLogger(__name__)


def _pairwise_merge(segments: List[AudioSegment]) -> AudioSegment:
    if len(segments) == 0:
        return AudioSegment.empty()
    if len(segments) == 1:
        return segments[0]

    while len(segments) > 1:
        merged = []
        i = 0
        remaining = len(segments)
        while i < remaining:
            if remaining - i == 3:
                merged.append(segments[i] + segments[i + 1] + segments[i + 2])
                i += 3
            elif remaining - i >= 2:
                merged.append(segments[i] + segments[i + 1])
                i += 2
            else:
                merged.append(segments[i])
                i += 1
        segments = merged

    return segments[0]


def _apply_id3_tags(
    mp3_bytes: bytes,
    title: str,
    author: Optional[str] = None,
    narrator: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[str] = None,
    description: Optional[str] = None,
    cover_image: Optional[bytes] = None,
    track_number: Optional[str] = None,
    album: Optional[str] = None,
) -> bytes:
    buf = io.BytesIO(mp3_bytes)
    audio = MP3(buf)

    if audio.tags is None:
        audio.add_tags()

    tags = audio.tags
    tags.add(TIT2(encoding=3, text=title))
    if album:
        tags.add(TALB(encoding=3, text=album))
    if author:
        tags.add(TPE1(encoding=3, text=author))
    if narrator:
        tags.add(TPE2(encoding=3, text=narrator))
    if genre:
        tags.add(TCON(encoding=3, text=genre))
    if year:
        tags.add(TDRC(encoding=3, text=year))
    if description:
        tags.add(COMM(encoding=3, lang="eng", desc="", text=description))
    if track_number:
        tags.add(TRCK(encoding=3, text=track_number))
    if cover_image:
        mime = "image/jpeg"
        if cover_image[:4] == b'\x89PNG':
            mime = "image/png"
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=cover_image))

    out = io.BytesIO()
    audio.save(out)
    return out.getvalue()


def _build_mp3_segment_with_progress(
    audio_blobs: List[bytes],
    pause_ms: int = 500,
    progress_callback: Optional[callable] = None,
    progress_start: float = 0.0,
    progress_end: float = 1.0,
) -> AudioSegment:
    silence = AudioSegment.silent(duration=pause_ms) if pause_ms > 0 else None
    total = max(len(audio_blobs), 1)
    decode_range = progress_end - progress_start
    decode_end = progress_start + decode_range * 0.6
    merge_start = decode_end

    decoded: List[AudioSegment] = []
    for i, blob in enumerate(audio_blobs):
        try:
            seg = AudioSegment.from_file(io.BytesIO(blob))
            if decoded and silence:
                decoded.append(silence)
            decoded.append(seg)
        except Exception as e:
            logger.warning(f"Skipping invalid audio blob (index {i}): {e}")
        if progress_callback and (i + 1) % max(1, total // 20) == 0:
            frac = progress_start + (decode_end - progress_start) * ((i + 1) / total)
            progress_callback(frac)

    if progress_callback:
        progress_callback(decode_end)

    if len(decoded) == 0:
        return AudioSegment.empty()

    import math
    total_rounds = max(1, math.ceil(math.log2(len(decoded))))
    current_round = 0
    segments = decoded
    while len(segments) > 1:
        merged = []
        idx = 0
        remaining = len(segments)
        while idx < remaining:
            if remaining - idx == 3:
                merged.append(segments[idx] + segments[idx + 1] + segments[idx + 2])
                idx += 3
            elif remaining - idx >= 2:
                merged.append(segments[idx] + segments[idx + 1])
                idx += 2
            else:
                merged.append(segments[idx])
                idx += 1
        segments = merged
        current_round += 1
        if progress_callback:
            frac = merge_start + (progress_end - merge_start) * (current_round / total_rounds)
            progress_callback(min(frac, progress_end))

    if progress_callback:
        progress_callback(progress_end)

    return segments[0]


def export_single_mp3(
    chapter_audio: List[Tuple[str, List[bytes]]],
    title: str,
    pause_ms: int = 500,
    author: Optional[str] = None,
    narrator: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[str] = None,
    description: Optional[str] = None,
    cover_image: Optional[bytes] = None,
    progress_callback: Optional[callable] = None,
) -> bytes:
    all_blobs = []
    for _ch_title, blobs in chapter_audio:
        all_blobs.extend(blobs)

    if progress_callback:
        progress_callback(0.0)
    combined = _build_mp3_segment_with_progress(all_blobs, pause_ms, progress_callback, 0.0, 0.5)
    if progress_callback:
        progress_callback(0.5)
    buf = io.BytesIO()
    combined.export(buf, format="mp3", bitrate="192k")
    if progress_callback:
        progress_callback(0.9)
    mp3_bytes = buf.getvalue()

    result = _apply_id3_tags(
        mp3_bytes, title=title, author=author, narrator=narrator,
        genre=genre, year=year, description=description,
        cover_image=cover_image, album=title,
    )
    if progress_callback:
        progress_callback(1.0)
    return result


def export_mp3_per_chapter(
    chapter_audio: List[Tuple[str, List[bytes]]],
    title: str,
    pause_ms: int = 500,
    author: Optional[str] = None,
    narrator: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[str] = None,
    description: Optional[str] = None,
    cover_image: Optional[bytes] = None,
    progress_callback: Optional[callable] = None,
) -> bytes:
    valid_chapters = [(ch_title, blobs) for ch_title, blobs in chapter_audio if blobs]
    total_chapters = max(1, len(valid_chapters))

    built_segments = []
    for ci, (ch_title, blobs) in enumerate(valid_chapters):
        ch_start = (ci / total_chapters) * 0.5
        ch_end = ((ci + 1) / total_chapters) * 0.5
        combined = _build_mp3_segment_with_progress(blobs, pause_ms, progress_callback, ch_start, ch_end)
        built_segments.append((ch_title, combined))
        if progress_callback:
            progress_callback(ch_end)

    if progress_callback:
        progress_callback(0.5)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for ci, (ch_title, combined) in enumerate(built_segments):
            mp3_buf = io.BytesIO()
            combined.export(mp3_buf, format="mp3", bitrate="192k")

            safe_title = ch_title or f"Chapter {ci + 1}"
            safe_title = "".join(c for c in safe_title if c.isalnum() or c in " _-").strip()
            filename = f"{ci + 1:02d} - {safe_title}.mp3"

            tagged = _apply_id3_tags(
                mp3_buf.getvalue(),
                title=safe_title,
                author=author,
                narrator=narrator,
                genre=genre,
                year=year,
                description=description,
                cover_image=cover_image,
                track_number=f"{ci + 1}/{len(chapter_audio)}",
                album=title,
            )
            zf.writestr(filename, tagged)
            if progress_callback:
                progress_callback(0.5 + 0.5 * ((ci + 1) / total_chapters))

    return zip_buf.getvalue()


def _parse_ffmpeg_progress(line: str) -> Optional[float]:
    import re
    m = re.search(r'out_time_ms=(\d+)', line)
    if m:
        return int(m.group(1)) / 1_000_000.0
    m = re.search(r'out_time=(\d+):(\d+):(\d+)\.(\d+)', line)
    if m:
        h, mn, s, frac_str = m.group(1), m.group(2), m.group(3), m.group(4)
        frac = int(frac_str) / (10 ** len(frac_str))
        return int(h) * 3600 + int(mn) * 60 + int(s) + frac
    m = re.search(r'time=(\d+):(\d+):(\d+)\.(\d+)', line)
    if m:
        h, mn, s, frac_str = m.group(1), m.group(2), m.group(3), m.group(4)
        frac = int(frac_str) / (10 ** len(frac_str))
        return int(h) * 3600 + int(mn) * 60 + int(s) + frac
    return None


def export_m4b(
    chapter_audio: List[Tuple[str, List[bytes]]],
    title: str,
    pause_ms: int = 500,
    author: Optional[str] = None,
    narrator: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[str] = None,
    description: Optional[str] = None,
    cover_image: Optional[bytes] = None,
    progress_callback: Optional[callable] = None,
) -> bytes:
    tmp_dir = tempfile.mkdtemp(prefix="m4b_export_")
    try:
        chapter_files = []
        chapter_meta = []
        cumulative_ms = 0
        total_ch = max(1, sum(1 for _, blobs in chapter_audio if blobs))
        built_count = 0

        for i, (ch_title, blobs) in enumerate(chapter_audio):
            if not blobs:
                continue

            ch_start = (built_count / total_ch) * 0.35
            ch_end = ((built_count + 1) / total_ch) * 0.35
            combined = _build_mp3_segment_with_progress(blobs, pause_ms, progress_callback, ch_start, ch_end)
            wav_path = os.path.join(tmp_dir, f"ch_{i:03d}.wav")
            combined.export(wav_path, format="wav")

            duration_ms = len(combined)
            chapter_meta.append({
                "title": ch_title or f"Chapter {i + 1}",
                "start_ms": cumulative_ms,
                "end_ms": cumulative_ms + duration_ms,
            })
            cumulative_ms += duration_ms
            chapter_files.append(wav_path)
            built_count += 1
            if progress_callback:
                progress_callback(ch_end)

        if not chapter_files:
            raise ValueError("No audio data to export")

        if progress_callback:
            progress_callback(0.35)

        concat_wav = os.path.join(tmp_dir, "full.wav")
        if len(chapter_files) == 1:
            os.rename(chapter_files[0], concat_wav)
        else:
            wav_segments = []
            total_wavs = len(chapter_files)
            for wi, wf in enumerate(chapter_files):
                wav_segments.append(AudioSegment.from_wav(wf))
                if progress_callback:
                    progress_callback(0.35 + 0.10 * ((wi + 1) / total_wavs))
            full = _pairwise_merge(wav_segments)
            if progress_callback:
                progress_callback(0.48)
            full.export(concat_wav, format="wav")

        if progress_callback:
            progress_callback(0.50)

        m4b_path = os.path.join(tmp_dir, "output.m4b")

        def _esc_ffmeta(val: str) -> str:
            return val.replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#").replace("\n", "\\\n")

        ffmetadata_path = os.path.join(tmp_dir, "chapters.txt")
        with open(ffmetadata_path, "w") as f:
            f.write(";FFMETADATA1\n")
            if title:
                f.write(f"title={_esc_ffmeta(title)}\n")
            if author:
                f.write(f"artist={_esc_ffmeta(author)}\n")
            if narrator:
                f.write(f"album_artist={_esc_ffmeta(narrator)}\n")
            if genre:
                f.write(f"genre={_esc_ffmeta(genre)}\n")
            if year:
                f.write(f"date={_esc_ffmeta(year)}\n")
            if description:
                f.write(f"comment={_esc_ffmeta(description)}\n")
            f.write("\n")

            for ch in chapter_meta:
                f.write("[CHAPTER]\n")
                f.write("TIMEBASE=1/1000\n")
                f.write(f"START={ch['start_ms']}\n")
                f.write(f"END={ch['end_ms']}\n")
                f.write(f"title={_esc_ffmeta(ch['title'])}\n")
                f.write("\n")

        total_duration_s = cumulative_ms / 1000.0

        cmd = [
            "ffmpeg", "-y",
            "-i", concat_wav,
            "-i", ffmetadata_path,
            "-map_metadata", "1",
            "-map_chapters", "1",
            "-c:a", "aac",
            "-b:a", "128k",
            "-progress", "pipe:2",
            "-f", "mp4",
            m4b_path,
        ]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        stderr_lines = []
        last_frac = 0.0
        try:
            for line in proc.stderr:
                stderr_lines.append(line)
                if progress_callback and total_duration_s > 0:
                    t = _parse_ffmpeg_progress(line)
                    if t is not None:
                        frac = min(t / total_duration_s, 1.0)
                        if frac > last_frac:
                            last_frac = frac
                            progress_callback(0.50 + frac * 0.50)
            proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise RuntimeError("ffmpeg encoding timed out")

        if proc.returncode != 0:
            stderr_text = "".join(stderr_lines)
            logger.error(f"ffmpeg failed: {stderr_text}")
            raise RuntimeError(f"ffmpeg encoding failed: {stderr_text[-500:]}")

        if cover_image:
            try:
                audio = MP4(m4b_path)
                mime = "image/jpeg"
                img_format = MP4Cover.FORMAT_JPEG
                if cover_image[:4] == b'\x89PNG':
                    mime = "image/png"
                    img_format = MP4Cover.FORMAT_PNG
                audio["covr"] = [MP4Cover(cover_image, imageformat=img_format)]
                if title:
                    audio["\xa9nam"] = [title]
                if author:
                    audio["\xa9ART"] = [author]
                if narrator:
                    audio["aART"] = [narrator]
                if genre:
                    audio["\xa9gen"] = [genre]
                if year:
                    audio["\xa9day"] = [year]
                if description:
                    audio["\xa9cmt"] = [description]
                audio.save()
            except Exception as e:
                logger.warning(f"Failed to embed cover art in M4B: {e}")

        with open(m4b_path, "rb") as f:
            return f.read()

    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
