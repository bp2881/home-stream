import os
import subprocess
import json


def convert_to_mp4():
    VIDEO_DIR = "media/"
    UNSUPPORTED_EXTS = ('.mkv', '.flv', '.avi', '.wmv', '.mov', '.mpeg', '.mpg', '.ts', '.vob', '.3gp', '.rm', '.rmvb')

    for file in os.listdir(VIDEO_DIR):
        full_path = os.path.join(VIDEO_DIR, file)

        if not os.path.isfile(full_path):
            continue

        if not file.lower().endswith(UNSUPPORTED_EXTS):
            continue

        base, ext = os.path.splitext(full_path)
        output_file = base + ".mp4"

        if os.path.exists(output_file):
            print(f"Already exists: {output_file}")
            continue

        print(f"Converting: {file} to {os.path.basename(output_file)}")

        command = [
            "ffmpeg",
            "-i", full_path,
            "-map", "0",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output_file
        ]

        try:
            subprocess.run(command, check=True)
            # Remove the original file
            #os.remove(full_path)
            print(f"Done: {os.path.basename(output_file)}")
        except subprocess.CalledProcessError:
            print(f"Error converting: {file}")

def list_videos():
    VIDEO_DIR = "media/"
    video_list = []

    for file in os.listdir(VIDEO_DIR):
        full_path = os.path.join(VIDEO_DIR, file)

        if not os.path.isfile(full_path):
            continue

        if not file.lower().endswith('.mp4'):
            continue

        video_list.append(file)

    with open("./static/videos.json", "w") as out:
        json.dump({"videos": video_list}, out)

    print(f"Video list saved to video_list.json with {len(video_list)} entries.")
