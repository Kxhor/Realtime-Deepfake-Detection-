import os
import requests

def download_model():
    model_path = "det_model/deepfake_detection_model.keras"
    
    if os.path.exists(model_path):
        print("Model already exists, skipping download.")
        return
    
    print("Downloading model from Hugging Face...")
    os.makedirs("det_model", exist_ok=True)
    
    url = "https://huggingface.co/kxhOR/deepfake-detection-model/resolve/main/deepfake_detection_model.keras"
    
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(model_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            percent = (downloaded / total * 100) if total else 0
            print(f"Downloading... {percent:.1f}%", end='\r')
    
    print("\nModel downloaded successfully!")

if __name__ == "__main__":
    download_model()