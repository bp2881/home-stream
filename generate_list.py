import os, json

MEDIA_DIR = "media"
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".avi", ".mov")

videos = [f for f in os.listdir(MEDIA_DIR) if f.lower().endswith(VIDEO_EXTS)]
with open("videos.json", "w") as out:
    json.dump({"videos": videos}, out)
