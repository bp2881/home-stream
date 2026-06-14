from __future__ import annotations
import hashlib
import json
import logging
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from config import (
    ALL_VIDEO_EXTS,
    BROWSER_SAFE_CODECS,
    CONVERTED_DIR,
    CONVERTIBLE_EXTS,
    MEDIA_DIR,
    SUBS_DIR,
    THUMB_DIR,
    THUMB_SCALE,
    THUMB_TIMESTAMP,
)
log = logging.getLogger("home-stream.media")
@dataclass
class SubTrack:
    index: int
    language: str
    label: str
    vtt_path: str
@dataclass
class MediaItem:
    id: str
    title: str
    path: str
    source_path: str
    duration: float
    thumb_url: str
    sub_tracks: List[SubTrack] = field(default_factory=list)
    converting: bool = False
_library: Dict[str, MediaItem] = {}
_lock    = threading.RLock()
_conv_queue: Set[str] = set()
_conv_lock  = threading.Lock()
def _make_id(abs_path: str) -> str:
    return hashlib.md5(abs_path.encode()).hexdigest()[:16]
def _nice_title(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[\._]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name
def _run(cmd: list, timeout: Optional[int] = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
def _probe_media(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    try:
        sz = os.path.getsize(path)
        if sz == 0:
            return None
        time.sleep(0.2)
        if os.path.getsize(path) != sz:
            return None
    except OSError:
        return None
    try:
        r = _run([
            "ffprobe", "-v", "quiet",
            "-show_format", "-show_streams",
            "-print_format", "json",
            path
        ], timeout=15)
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        video_codec = "unknown"
        sub_streams = []
        for s in data.get("streams", []):
            ctype = s.get("codec_type")
            if ctype == "video" and video_codec == "unknown":
                video_codec = s.get("codec_name", "unknown").lower()
            elif ctype == "subtitle":
                sub_streams.append(s)
        if video_codec == "unknown":
            return None
        return {
            "duration": duration,
            "video_codec": video_codec,
            "sub_streams": sub_streams
        }
    except Exception as exc:
        log.warning("Probe failed for %s: %s", path, exc)
        return None
def _extract_thumbnail(video_path: str, out_path: str) -> None:
    if os.path.exists(out_path):
        return
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    _run([
        "ffmpeg", "-y",
        "-ss", THUMB_TIMESTAMP,
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"scale={THUMB_SCALE}",
        "-q:v", "3",
        out_path,
    ], timeout=30)
def _extract_subtitle(video_path: str, stream_idx: int, out_path: str) -> bool:
    if os.path.exists(out_path) and os.path.getsize(out_path) > 25:
        return True
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    log.info("Extracting subtitle stream %d from %s", stream_idx, os.path.basename(video_path))
    r = _run([
        "ffmpeg", "-y", "-i", video_path,
        "-map", f"0:s:{stream_idx}",
        "-c:s", "webvtt",
        out_path,
    ], timeout=120)
    if r.returncode != 0:
        log.error("Subtitle extraction failed (stream %d, %s):\n%s",
                  stream_idx, os.path.basename(video_path), r.stderr[-600:])
        if os.path.exists(out_path):
            os.remove(out_path)
        return False
    if not os.path.exists(out_path) or os.path.getsize(out_path) <= 25:
        log.warning("Subtitle file empty (no cues) after extraction: %s", out_path)
        if os.path.exists(out_path):
            os.remove(out_path)
        return False
    with open(out_path, "r", errors="replace") as f:
        header = f.read(20)
    if "WEBVTT" not in header:
        log.error("Extracted file is not valid VTT (no WEBVTT header): %s", out_path)
        os.remove(out_path)
        return False
    log.info("Subtitle extracted OK → %s (%d bytes)",
             os.path.basename(out_path), os.path.getsize(out_path))
    return True
def _srt_to_vtt(srt_text: str) -> str:
    vtt = "WEBVTT\n\n"
    vtt += re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt_text)
    return vtt
def _conversion_worker(item_id: str, source: str, dest: str, transcode: bool = False) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if transcode:
        log.info("Transcoding (full re-encode) %s → %s", source, dest)
        r = _run([
            "ffmpeg", "-y", "-i", source,
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-movflags", "faststart",
            dest,
        ], timeout=None)
    else:
        log.info("Remuxing (codec copy) %s → %s", source, dest)
        r = _run([
            "ffmpeg", "-y", "-i", source,
            "-c", "copy", "-movflags", "faststart",
            dest,
        ], timeout=None)
    with _conv_lock:
        _conv_queue.discard(source)
    with _lock:
        item = _library.get(item_id)
        if item is None:
            return
        if r.returncode == 0:
            log.info("Conversion done: %s", dest)
            item.converting = False
            item.path       = dest
            probe = _probe_media(dest)
            item.duration   = probe["duration"] if probe else 0.0
        else:
            log.error("Conversion failed for %s:\n%s", source, r.stderr[-500:])
            item.converting = False
def _build_item(abs_path: str) -> Optional[MediaItem]:
    probe = _probe_media(abs_path)
    if not probe:
        log.warning("File is not ready or is invalid/corrupt: %s", abs_path)
        return None
    ext = os.path.splitext(abs_path)[1].lower()
    media_id = _make_id(abs_path)
    title = _nice_title(os.path.basename(abs_path))
    thumb_path = os.path.join(THUMB_DIR, f"{media_id}.jpg")
    thumb_url  = f"/thumb/{media_id}"
    converting = False
    transcode  = False
    codec = probe["video_codec"]
    if codec not in BROWSER_SAFE_CODECS:
        log.info("Unsupported codec %r in %s — will transcode to H.264", codec, abs_path)
        os.makedirs(CONVERTED_DIR, exist_ok=True)
        converted_path = os.path.join(CONVERTED_DIR, f"{media_id}.mp4")
        if os.path.exists(converted_path):
            playable = converted_path
        else:
            playable   = converted_path
            converting = True
            transcode  = True
    elif ext in CONVERTIBLE_EXTS:
        mp4_path = os.path.splitext(abs_path)[0] + ".mp4"
        if os.path.exists(mp4_path):
            playable = mp4_path
        else:
            playable   = mp4_path
            converting = True
            transcode  = False
    else:
        playable = abs_path
    try:
        _extract_thumbnail(abs_path, thumb_path)
    except Exception as exc:
        log.warning("Thumbnail failed for %s: %s", abs_path, exc)
    if not os.path.exists(thumb_path):
        thumb_url = "/static/no_thumb.svg"
    sub_tracks: List[SubTrack] = []
    for i, s in enumerate(probe["sub_streams"]):
        tags = s.get("tags", {})
        lang  = tags.get("language", f"track{i}")
        label = tags.get("title", lang.upper())
        vtt_path = os.path.join(SUBS_DIR, f"{media_id}_{i}.vtt")
        ok = _extract_subtitle(abs_path, i, vtt_path)
        if ok:
            sub_tracks.append(SubTrack(index=i, language=lang, label=label, vtt_path=vtt_path))
    base_no_ext = os.path.splitext(abs_path)[0]
    for sib_ext in (".srt", ".vtt"):
        sib = base_no_ext + sib_ext
        if os.path.exists(sib):
            vtt_out = os.path.join(SUBS_DIR, f"{media_id}_sib{sib_ext.replace('.','')}.vtt")
            if sib_ext == ".srt":
                if not os.path.exists(vtt_out):
                    os.makedirs(SUBS_DIR, exist_ok=True)
                    with open(sib, "r", errors="replace") as f:
                        content = _srt_to_vtt(f.read())
                    with open(vtt_out, "w") as f:
                        f.write(content)
            else:
                vtt_out = sib
            if os.path.exists(vtt_out):
                idx = len(sub_tracks)
                sub_tracks.append(SubTrack(index=idx, language="ext", label="External", vtt_path=vtt_out))
    duration = probe["duration"]
    if converting and os.path.exists(playable):
        p2 = _probe_media(playable)
        if p2: duration = p2["duration"]
    item = MediaItem(
        id=media_id,
        title=title,
        path=playable,
        source_path=abs_path,
        duration=duration,
        thumb_url=thumb_url,
        sub_tracks=sub_tracks,
        converting=converting,
    )
    if converting:
        _start_conversion(media_id, abs_path, playable, transcode=transcode)
    return item
def _start_conversion(item_id: str, source: str, dest: str, transcode: bool = False) -> bool:
    with _conv_lock:
        if source in _conv_queue:
            return False
        _conv_queue.add(source)
    t = threading.Thread(
        target=_conversion_worker,
        args=(item_id, source, dest, transcode),
        daemon=True,
    )
    t.start()
    return True
def _collect_video_files() -> List[str]:
    files: List[str] = []
    for dirpath, _, filenames in os.walk(MEDIA_DIR):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in ALL_VIDEO_EXTS:
                files.append(os.path.abspath(os.path.join(dirpath, fname)))
    return files
def _files_to_process(all_files: List[str]) -> List[str]:
    mp4_set = {f for f in all_files if f.endswith(".mp4")}
    result: List[str] = []
    for f in all_files:
        ext = os.path.splitext(f)[1].lower()
        if ext in CONVERTIBLE_EXTS:
            if os.path.splitext(f)[0] + ".mp4" in mp4_set:
                continue
        result.append(f)
    return result
def scan() -> None:
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(THUMB_DIR, exist_ok=True)
    os.makedirs(SUBS_DIR,  exist_ok=True)
    all_files  = _collect_video_files()
    to_process = _files_to_process(all_files)
    log.info("Scanning %d video file(s) in %s", len(to_process), MEDIA_DIR)
    with _conv_lock:
        currently_converting = set(_conv_queue)
    new_items: Dict[str, MediaItem] = {}
    for abs_path in to_process:
        media_id = _make_id(abs_path)
        with _lock:
            existing = _library.get(media_id)
        if existing is not None:
            new_items[media_id] = existing
            continue
        if abs_path in currently_converting:
            continue
        try:
            item = _build_item(abs_path)
            if item:
                new_items[item.id] = item
        except Exception as exc:
            log.exception("Failed to build item for %s: %s", abs_path, exc)
    with _lock:
        _library.clear()
        _library.update(new_items)
    log.info("Library ready — %d item(s)", len(_library))
def get_all() -> List[MediaItem]:
    with _lock:
        return sorted(_library.values(), key=lambda i: i.title.lower())
def get_item(media_id: str) -> Optional[MediaItem]:
    with _lock:
        return _library.get(media_id)
def library_as_json() -> list:
    with _lock:
        return [
            {
                "id":         i.id,
                "title":      i.title,
                "duration":   i.duration,
                "thumb_url":  i.thumb_url,
                "converting": i.converting,
                "subs":       len(i.sub_tracks),
            }
            for i in get_all()
        ]
def _watcher_tick() -> None:
    try:
        all_files  = _collect_video_files()
        to_process = _files_to_process(all_files)
        for abs_path in to_process:
            media_id = _make_id(abs_path)
            with _lock:
                already_tracked = media_id in _library
            if already_tracked:
                continue
            with _conv_lock:
                in_flight = abs_path in _conv_queue
            if in_flight:
                continue
            log.info("Watcher: new file → %s", abs_path)
            try:
                item = _build_item(abs_path)
                if item:
                    with _lock:
                        _library[item.id] = item
            except Exception as exc:
                log.exception("Watcher: failed to process %s: %s", abs_path, exc)
        with _lock:
            stale = [
                item for item in _library.values()
                if item.converting and os.path.exists(item.path)
            ]
        for item in stale:
            log.warning("Watcher: fixing stuck item %s", item.title)
            with _lock:
                live = _library.get(item.id)
                if live and live.converting and os.path.exists(live.path):
                    live.converting = False
                    live.duration   = _ffprobe_duration(live.path)
    except Exception as exc:
        log.exception("Watcher tick error: %s", exc)
def start_watcher(interval: int = 30) -> None:
    def _loop():
        log.info("FileWatcher started — polling every %ds", interval)
        while True:
            time.sleep(interval)
            _watcher_tick()
    t = threading.Thread(target=_loop, name="home-stream-watcher", daemon=True)
    t.start()