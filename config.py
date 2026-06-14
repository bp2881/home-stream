import os
MEDIA_DIR   = os.environ.get("HOMESTREAM_MEDIA_DIR",  "media/")
CACHE_DIR   = os.environ.get("HOMESTREAM_CACHE_DIR",  "cache/")
THUMB_DIR   = os.path.join(CACHE_DIR, "thumbs")
SUBS_DIR    = os.path.join(CACHE_DIR, "subs")
HOST        = os.environ.get("HOMESTREAM_HOST", "0.0.0.0")
PORT        = int(os.environ.get("HOMESTREAM_PORT", "5000"))
CHUNK_SIZE       = 1024 * 1024
WATCHER_INTERVAL = int(os.environ.get("HOMESTREAM_WATCHER_INTERVAL", "30"))
THUMB_TIMESTAMP = "00:00:05"
THUMB_SCALE     = "320:180"
NATIVE_EXTS      = {".mp4"}
CONVERTIBLE_EXTS = {
    ".mkv", ".webm", ".mov", ".flv", ".avi", ".wmv",
    ".mpeg", ".mpg", ".ts", ".m2ts", ".mts",
    ".vob", ".3gp", ".rm", ".rmvb", ".m4v",
    ".ogv", ".ogg",
}
ALL_VIDEO_EXTS   = NATIVE_EXTS | CONVERTIBLE_EXTS
BROWSER_SAFE_CODECS = {"h264", "avc", "avc1"}
CONVERTED_DIR = os.path.join(CACHE_DIR, "converted")