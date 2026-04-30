import tensorflow as tf
import cv2
import numpy as np
import os

print("Loading model for video detection...")
model = tf.keras.models.load_model(
    os.path.join("det_model", "deepfake_detection_model.keras"),
    compile=False
)
print("Model ready!")

def extract_frames(video_path, output_size=(128, 128), frame_count=10):
    cap = cv2.VideoCapture(video_path)
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(total_frames // frame_count, 1)
    for i in range(frame_count):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * step)
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, output_size)
        frames.append(frame)
    cap.release()
    frames = np.array(frames) / 255.0
    return np.expand_dims(frames, axis=0)

def predict_video(video_path):
    frames = extract_frames(video_path)
    output_data = model.predict(frames, verbose=0)
    predicted_class = np.argmax(output_data, axis=1)[0]
    confidence = output_data[0][predicted_class] * 100
    label = "FAKE" if predicted_class == 1 else "REAL"
    return {"label": label, "confidence": confidence}