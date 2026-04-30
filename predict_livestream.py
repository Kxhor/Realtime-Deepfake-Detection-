import json
import cv2
import yt_dlp
import numpy as np
import tensorflow as tf
from urllib.parse import urlparse, parse_qs

stop_streaming = False

# Load Keras model directly — no TFLite needed
print("Loading model...")
model = tf.keras.models.load_model(
    "det_model/deepfake_detection_model.keras",
    compile=False
)
print("Model loaded!")

# Constants
TIMESTEPS = 10
FRAME_HEIGHT = 128
FRAME_WIDTH = 128

def get_embed_url(youtube_url):
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        query_params = parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
    elif parsed_url.hostname == 'youtu.be':
        video_id = parsed_url.path.lstrip('/')
    else:
        return None
    if video_id:
        return f"https://www.youtube.com/embed/{video_id}"
    return None

def get_youtube_stream_url(youtube_url):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']

def process_video_segment(segment):
    segment = np.expand_dims(segment, axis=0).astype(np.float32)
    output_data = model.predict(segment, verbose=0)
    label_idx = np.argmax(output_data)
    confidence = output_data[0][label_idx]
    return "Deepfake" if label_idx == 1 else "Real", confidence

def resize_and_normalize(frame):
    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    frame = frame / 255.0
    return frame

def capture_youtube_stream(youtube_url):
    global stop_streaming
    best_url = get_youtube_stream_url(youtube_url)
    print("best url: ", best_url)
    cap = cv2.VideoCapture(best_url)

    if not cap.isOpened():
        print("Failed to open video stream.")
        return {"error": "Unable to open stream"}

    frame_sec = 1
    frame_buffer = []
    real_weight = 0.0
    fake_weight = 0.0
    result = []

    while cap.isOpened():
        if stop_streaming:
            print("Streaming stopped by user.")
            break

        ret, frame = cap.read()
        if not ret:
            print("Stream ended or failed.")
            break

        resized_frame = resize_and_normalize(frame)
        frame_buffer.append(resized_frame)

        if len(frame_buffer) == TIMESTEPS:
            label, confidence = process_video_segment(np.array(frame_buffer))
            confidence = confidence * 100
            if label == "Real":
                real_weight += confidence
            else:
                fake_weight += confidence

            result.append({
                "Second": frame_sec,
                "final": {"prediction": label, "Confidence": confidence}
            })

            with open("current_results.json", "w") as f:
                json.dump({"results": result}, f)

            frame_sec += 1
            frame_buffer = []

    final_label = "Real" if real_weight > fake_weight else "Deepfake"
    final_confidence = max(real_weight, fake_weight) / max(frame_sec - 1, 1)
    final_result = {"FinalPrediction": {"label": final_label, "confidence": final_confidence}}

    cap.release()
    print(result)
    print(final_result)
    return [result, final_result]