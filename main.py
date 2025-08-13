from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import subprocess
import tempfile
import os
import requests
from supabase import create_client
import uuid
import shutil

from cli import process_video

# ===== Supabase Config =====
# ====== Load environment variables ======
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "test")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
OUTPUT_DIR = "processed_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()

class VideoRequest(BaseModel):
    video_url: str

def download_file(url, dest_path):
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)

def upload_to_supabase(file_path, object_name):
    with open(file_path, "rb") as f:
        supabase.storage.from_(BUCKET_NAME).upload(
            file=f,
            path=object_name,
            file_options={
                "content-type": "video/mp4",
                "upsert": "true"
            }
        )
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{object_name}"

def notify_n8n(public_url):
    try:
        r = requests.post(N8N_WEBHOOK_URL, json={"video_url": public_url})
        r.raise_for_status()
        print("✅ Sent to n8n:", public_url)
    except Exception as e:
        print("❌ Failed to send to n8n:", e)

@app.post("/process")
def process_video_from_url(req: VideoRequest, background_tasks: BackgroundTasks):
    video_id = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp()
    input_path = os.path.join(tmp_dir, f"{video_id}.mp4")
    output_path = os.path.join(OUTPUT_DIR, f"{video_id}_output.mp4")

    try:
        download_file(req.video_url, input_path)
    except Exception as e:
        shutil.rmtree(tmp_dir)
        return {"status": "error", "message": f"Failed to download video: {str(e)}"}

    def run_processing():
        try:
            process_video(input_path, None, output_path)  # YOUR EDITING FUNCTION
            public_url = upload_to_supabase(output_path, f"uploads/{video_id}output.mp4")
            notify_n8n(public_url)
        except Exception as e:
            print("[ERROR] Processing failed:", e)
        finally:
            shutil.rmtree(tmp_dir)
            if os.path.exists(output_path):
                os.remove(output_path)

    background_tasks.add_task(run_processing)

    return {"status": "processing_started"}
