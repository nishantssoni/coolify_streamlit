import argparse
import json
import base64
import tempfile
import os
import requests
import subprocess
import re
import sys
import ntplib
from time import time

# Cutoff timestamp (UTC) — Example: 14 Aug 2025 00:00 UTC
CUTOFF_TIMESTAMP = 1755109020
ENCRYPTION_KEY = "videokey"

# Embedded fallback preset
MY_PRESET_DATA = b"DUsCDAMfAAsFS15FFEkHCx8ODBEBDhYKVFNEVUFdV0pFWFxWV15TTEZbVlFdR0VbFQYKER0KFg1UU0RXQV9UTkFbVVBeU1xBQVpQVFdHRVsFCBAQHQoREBkHRl9PWktPRVtTUVxYU0tOWlVdWlNRVVZLBgkOCA4mAQENEQpJX1kQCAgWCkdFWxQFERdNUUUfFwUXAENLRxsaHBY6HQoBEAMaRl9PW0tAT1xQUlpaVEpHW1ZUWFpcBFpJRgwCCgIcBUteRTQQRwwEBUZfT0kNDQIZF19ARBYMBggGBBwOSx8TBBAKGw4GEVgACgMARBYNGRsFAgpEE0hZBgYPCggRVgYcBgkGCEoNExoQSkAHCh4ZRxQLCElJWVQBOxUAGAwNHwYKR1VLRxUTDxBHQ0tHDykZCxYGHwwWGEteRU0fCglURURHABsEGh8dHUdVS1VXTlFWVlpZXE1HWFNTW1xVT1pJRhYMCgkcVFNEVEFTU0tAXFRTX1lRSU9fV11aFklZDUsRFwNJX1lUARARHxhfVlkaERUOCQQKE0cCAAIfCg0TCgxLBgUDFlkaEAodCgIcWR9VSgAJDxwVHUsVGgkJEBVGEAAcH0pWGgYDCkEbCx5URURHBzQVFgUAEAwABUdDVksWDAgDEVtaSUYTMBsKCh8dDQoBSV9ZVAsLERsECFtaSUYKHwoGEAIQRl9PWktJWklGFgwKCRxUU0RVQV9QTUBfUlNZXVNPQF9SU1ldGCQL"

def get_ntp_time():
    try:
        client = ntplib.NTPClient()
        response = client.request('time.google.com', version=3)
        return int(response.tx_time)
    except:
        return int(time())  # fallback

def xor_encrypt_decrypt(data: bytes, key: str) -> bytes:
    key_bytes = key.encode()
    return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data)])

def download_image(url, folder):
    local_path = os.path.join(folder, os.path.basename(url.split("?")[0]))
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)
    return local_path

def get_position_coordinates(h_pos, v_pos):
    x_positions = {
        'left': '10',
        'center': '(main_w-overlay_w)/2',
        'right': 'main_w-overlay_w-10'
    }
    y_positions = {
        'top': '10',
        'center': '(main_h-overlay_h)/2',
        'bottom': 'main_h-overlay_h-10'
    }
    return x_positions[h_pos], y_positions[v_pos]

def process_video(video_path, preset_path, output_path):
    # Decide which preset to use
    if get_ntp_time() > CUTOFF_TIMESTAMP:
        encrypted = MY_PRESET_DATA
        print("[INFO] Using embedded owner preset due to expiration.")
    else:
        print(f"[INFO] Using client preset. Current time: {get_ntp_time()}")
        with open(preset_path, "rb") as f:
            encrypted = f.read()

    decrypted_json = xor_encrypt_decrypt(base64.b64decode(encrypted), ENCRYPTION_KEY)
    preset = json.loads(decrypted_json.decode())

    # Get total duration
    dur_proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        total_duration = float(dur_proc.stdout.strip())
    except ValueError:
        print("[ERROR] Could not get video duration.")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        video_input = ["-i", video_path]
        filter_parts = []
        input_count = 1
        label_counter = 0
        current_label = "[0:v]"

        # Apply filters
        f = preset["filters"]
        if f["brightness"] != 0.0 or f["contrast"] != 1.0:
            next_label = f"[v{label_counter}]"
            filter_parts.append(f"{current_label}eq=brightness={f['brightness']}:contrast={f['contrast']}{next_label}")
            current_label = next_label
            label_counter += 1
        if f["saturation"] != 1.0:
            next_label = f"[v{label_counter}]"
            filter_parts.append(f"{current_label}eq=saturation={f['saturation']}{next_label}")
            current_label = next_label
            label_counter += 1
        if f["black_white"]:
            next_label = f"[v{label_counter}]"
            filter_parts.append(f"{current_label}hue=s=0{next_label}")
            current_label = next_label
            label_counter += 1
        if f["blur"] and f["blur_radius"] > 0:
            next_label = f"[v{label_counter}]"
            filter_parts.append(f"{current_label}gblur=sigma={f['blur_radius']}{next_label}")
            current_label = next_label
            label_counter += 1

        # Overlays
        for idx, img in enumerate(preset["images"]):
            img_path = download_image(img["url"], tmpdir)
            video_input.extend(["-i", img_path])

            filters_for_img = []
            if img["scale"] != 1.0:
                filters_for_img.append(f"scale=iw*{img['scale']}:ih*{img['scale']}")
            if img["opacity"] < 1.0:
                filters_for_img.append(f"format=rgba,colorchannelmixer=aa={img['opacity']}")

            if filters_for_img:
                filter_parts.append(f"[{input_count}:v]{','.join(filters_for_img)}[img{idx}]")
            else:
                filter_parts.append(f"[{input_count}:v]copy[img{idx}]")

            x_pos, y_pos = get_position_coordinates(img["h_position"], img["v_position"])
            next_label = f"[v{label_counter}]"
            filter_parts.append(f"{current_label}[img{idx}]overlay=x={x_pos}:y={y_pos}{next_label}")
            current_label = next_label
            label_counter += 1
            input_count += 1

        filter_complex = ";".join(filter_parts) if filter_parts else None

        ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg") if getattr(sys, 'frozen', False) else "ffmpeg"
        
        cmd = [ffmpeg_path, *video_input]
        if filter_complex:
            cmd += ["-filter_complex", filter_complex, "-map", current_label]
        else:
            cmd += ["-map", "0:v"]

        cmd += ["-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "copy", output_path]

        print("\n[DEBUG] Running FFmpeg command:\n", " ".join(cmd), "\n")

        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
        time_re = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        for line in proc.stderr:
            match = time_re.search(line)
            if match:
                h, m, s = match.groups()
                elapsed = int(h) * 3600 + int(m) * 60 + float(s)
                percent = min(100, (elapsed / total_duration) * 100)
                print(f"\rProgress: {percent:.2f}%", end="")
        proc.wait()

        if proc.returncode != 0:
            print("\n[ERROR] FFmpeg failed.")
        else:
            print("\n[INFO] Video processing completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal-based Video Processor")
    parser.add_argument("-v", "--video", required=True, help="Path to input video")
    parser.add_argument("-p", "--preset", required=False, help="Path to preset .vpf file")
    parser.add_argument("-o", "--output", required=True, help="Path to output video file")
    args = parser.parse_args()

    process_video(args.video, args.preset, args.output)
