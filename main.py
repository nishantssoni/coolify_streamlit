from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import tempfile
import os
import requests
import uuid
import shutil

# import your processing function from the CLI script
from cli import process_video

app = FastAPI()

class VideoRequest(BaseModel):
    video_url: str

OUTPUT_DIR = "processed_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_file(url, dest_path):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)

@app.post("/process")
def process_video_from_url(req: VideoRequest, background_tasks: BackgroundTasks):
    video_id = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, f"{video_id}.mp4")
    output_path = os.path.join(OUTPUT_DIR, f"{video_id}_output.mp4")

    # Download video
    try:
        download_file(req.video_url, input_path)
    except Exception as e:
        shutil.rmtree(tmp_dir)
        return {"status": "error", "message": f"Failed to download video: {str(e)}"}

    # Run video processing in background
    def run_processing():
        try:
            # No preset path, will use embedded if expired
            process_video(input_path, None, output_path)
        except Exception as e:
            print("[ERROR] Processing failed:", e)
        finally:
            shutil.rmtree(tmp_dir)

    background_tasks.add_task(run_processing)

    return {
        "status": "processing_started",
        "output_file": output_path
    }

