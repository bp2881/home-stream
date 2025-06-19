import os
import subprocess
import json

VIDEO_DIR = "media/"
VIDEO_URL_PREFIX = "/media/"
UNSUPPORTED_EXTS = (
    '.mkv', '.flv', '.avi', '.wmv', '.mov', '.mpeg',
    '.mpg', '.ts', '.vob', '.3gp', '.rm', '.rmvb'
)


def convert_to_mp4():
    for file in os.listdir(VIDEO_DIR):
        full_path = os.path.join(VIDEO_DIR, file)

        if not os.path.isfile(full_path):
            continue

        if not file.lower().endswith(UNSUPPORTED_EXTS):
            continue

        base, _ = os.path.splitext(full_path)
        output_file = base + ".mp4"

        if os.path.exists(output_file):
            print(f"Already exists: {output_file}")
            continue

        print(f"Converting: {file} to {os.path.basename(output_file)}")
        command = [
            "ffmpeg", "-i", full_path,
            "-threads", "4",
            "-codec", "copy",
            "-movflags", "faststart",  # ensure fast playback
            output_file
        ]

        try:
            subprocess.run(command, check=True)
            # Optionally remove original:
            # os.remove(full_path)
            print(f"Done: {os.path.basename(output_file)}")
        except subprocess.CalledProcessError:
            print(f"Error converting: {file}")


def list_videos():
    for file in os.listdir(VIDEO_DIR):
        full_path = os.path.join(VIDEO_DIR, file)

        if not os.path.isfile(full_path):
            continue

        if not file.lower().endswith('.mp4'):
            continue

        video_info = {
            "name": file,
            "url": VIDEO_URL_PREFIX + file
        }

        with open("videos.json", "w") as file:
            json.dump(video_info, file, indent=4)
    


# If run directly, regenerate video list
if __name__ == "__main__":
    convert_to_mp4()
    list_videos()
