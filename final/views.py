from django.shortcuts import render
import json
from .models import Video, Stream, Detection,UploadedVideo
from itertools import chain
from .forms import Video_form, Stream_form,VerifyForm
from det_model.videodet import predict_video  # Import your deepfake detection function
from predict_livestream import capture_youtube_stream, get_embed_url
import os
from django.conf import settings
from blockchain import get_detection_result, process_file
# Home view
def home(request):
    return render(request, "main/base.html", {})

# Video analysis view
# Video analysis view
def video(request):
    all_video = Video.objects.all()
    prediction_result = None  # To store prediction result

    if request.method == "POST":
        form = Video_form(data=request.POST, files=request.FILES)
        if 'clear' in request.POST:  # Clear button pressed
            # Clear the previous detection process
            for video in all_video:
                if video.pk:  # Ensure only saved instances are deleted
                    # Delete the file from media storage
                    video.video.delete(save=False)  # Don't save after deletion
                    video.delete()  # Delete the record from the database
            return render(request, "main/video.html", {"form": form})
        else:
            if form.is_valid():
                video_instance = form.save()  # Save the uploaded video to the database
                video_path = os.path.join(settings.MEDIA_ROOT, str(video_instance.video))  # Get the video file path
                
                # Perform deepfake detection
                try:
                    prediction_result = predict_video(video_path)
                    process_file(video_path)  # Store the video hash on the blockchain
                    result = prediction_result.get('label', 'No result')  # Modify this based on your prediction format

                    # Create a new Detection entry
                    Detection.objects.create(
                        timestamp=video_instance.created_at,
                        type='Video',
                        link=video_instance.video.url,
                        result=result
                    )
                except Exception as e:
                    prediction_result = {"label": "Error", "confidence": 0.0}
                    print(f"Error during prediction: {e}")
                
                # Return success message and prediction result
                return render(request, 'main/video.html', {
                    "form": form,
                    "all": all_video,
                    "result": prediction_result
                })
    else:
        form = Video_form()

    return render(request, 'main/video.html', {"form": form, "all": all_video})


# Stream analysis view
from django.http import JsonResponse
from threading import Thread
import time

# Global variable to control the streaming process
stop_streaming = False

"""def stream(request):
    global stop_streaming
    all_stream = Stream.objects.all()

    if request.method == 'POST':
        form = Stream_form(data=request.POST)
        if 'clear' in request.POST:
            # Clear the previous detection process
            for strm in all_stream:
                if strm.pk:  # Check if the object exists in the database
                    if strm.yt_url:
                        strm.yt_url = None
                    strm.delete()
            return render(request, "main/stream.html", {"form": form})

        elif 'stop' in request.POST:
            # Stop the streaming process
            stop_streaming = True
            return JsonResponse({"status": "Streaming stopped."})

        else:
            if form.is_valid():
                stream_instance = form.save()
                yt_url = stream_instance.yt_url
                print("yt url: ", yt_url)
                strm_url = get_embed_url(yt_url)

                # Start a thread to process the stream asynchronously
                stop_streaming = False

                def process_stream():
                    try:
                        prediction_result, final_result = capture_youtube_stream(yt_url)
                        result = final_result.get('FinalPrediction', {}).get('label', 'No result')

                        # Create a new Detection entry
                        Detection.objects.create(
                            timestamp=stream_instance.created_at,
                            type='Stream',
                            link=stream_instance.yt_url,
                            result=result
                        )
                    except Exception as e:
                        print("Error in prediction:", e)

                Thread(target=process_stream).start()

                return render(request, 'main/stream.html', {
                    "form": form,
                    "all": all_stream,
                    "embed": strm_url,
                })

    else:
        form = Stream_form()

    return render(request, "main/stream.html", {"form": form, "all": all_stream})"""

from django.http import JsonResponse

def stream(request):
    global stop_streaming
    all_stream = Stream.objects.all()
    final_prediction = None  # To store the final prediction result

    if request.method == 'POST':
        form = Stream_form(data=request.POST)
        if 'clear' in request.POST:
            # Clear the previous detection process
            for strm in all_stream:
                if strm.pk:
                    if strm.yt_url:
                        strm.yt_url = None
                    strm.delete()
            return render(request, "main/stream.html", {"form": form})

        elif 'stop' in request.POST:
            # Stop the streaming process
            stop_streaming = True
            # Return the final prediction result
            if final_prediction:
                return JsonResponse({
                    "status": "stopped",
                    "final_prediction": final_prediction.get('FinalPrediction', {}).get('label', 'No result'),
                    "confidence": final_prediction.get('FinalPrediction', {}).get('confidence', 0.0)
                })
            else:
                return JsonResponse({"status": "stopped", "final_prediction": None, "confidence": None})

        else:
            if form.is_valid():
                stream_instance = form.save()
                yt_url = stream_instance.yt_url
                print("yt url: ", yt_url)
                strm_url = get_embed_url(yt_url)

                # Start a thread to process the stream asynchronously
                stop_streaming = False

                def process_stream():
                    nonlocal final_prediction
                    try:
                        for prediction_result, final_result in capture_youtube_stream(yt_url):
                            if stop_streaming:
                                break
                            final_prediction = final_result

                        # Save final prediction in the database if streaming completes
                        if final_prediction:
                            result_label = final_prediction.get('FinalPrediction', {}).get('label', 'No result')
                            print("RESULT LABEL: ", result_label)
                            Detection.objects.create(
                                timestamp=stream_instance.created_at,
                                type='Stream',
                                link=stream_instance.yt_url,
                                result=result_label
                            )
                    except Exception as e:
                        print("Error in prediction:", e)

                Thread(target=process_stream).start()

                return render(request, 'main/stream.html', {
                    "form": form,
                    "all": all_stream,
                    "embed": strm_url
                })

    else:
        form = Stream_form()

    return render(request, "main/stream.html", {"form": form, "all": all_stream})



def fetch_results(request):
    try:
        # Read JSON file
        file_path = os.path.join(settings.BASE_DIR, 'current_results.json')
        with open(file_path, 'r') as f:
            data = json.load(f)  # Load the data from JSON file
    except FileNotFoundError:
        data = {"results": []}  # If the file does not exist, return empty results

    # Pass the data to the template
    return JsonResponse(data) 


# History view to display detection results for both videos and streams
def history(request):
    # Fetch data from both Video and Stream models
    video_detections = Video.objects.all().order_by('created_at')  # Get all videos sorted by timestamp
    stream_detections = Stream.objects.all().order_by('created_at')  # Get all streams sorted by timestamp

    # Fetch all detections related to video and stream URLs
    video_urls = [video.video.url for video in video_detections if video.video]  # Only include videos with files
    stream_urls = [stream.yt_url for stream in stream_detections]

    # Fetch detections using links (video URLs or stream URLs)
    detections = Detection.objects.filter(
        link__in=video_urls + stream_urls
    )

    # Create a dictionary of detections by link (video.url or stream.yt_url)
    detection_dict = {detection.link: detection for detection in detections}

    # Create a list of detection data to pass to the template
    detection_data = []

    # Add video detections
    for video in video_detections:
        if video.video:  # Check if video has a file associated with it
            result = detection_dict.get(video.video.url, None)  # Get the detection result for the video URL
            detection_data.append({
                'timestamp': video.created_at,
                'type': 'Video',
                'link': video.video.url,
                'result': result.result if result else "No result"  # If no detection, set "No result"
            })

    # Add stream detections
    for stream in stream_detections:
        result = detection_dict.get(stream.yt_url, None)  # Get the detection result for the stream URL
        detection_data.append({
            'timestamp': stream.created_at,
            'type': 'Stream',
            'link': stream.yt_url,
            'result': result.result if result else "No result"  # If no detection, set "No result"
        })

    # Sort combined detections by timestamp (in descending order)
    detection_data.sort(key=lambda x: x['timestamp'], reverse=True)

    return render(request, 'main/history.html', {'detections': detection_data})

def real(request):
    form = VerifyForm(files=request.FILES)
    if request.method == "POST":
        form = VerifyForm(request.POST, request.FILES)
        if form.is_valid():
            video_instance = form.save()  # Save the uploaded video to the database
            video_path = os.path.join(settings.MEDIA_ROOT, str(video_instance.video))  # Get the video file path
            result = get_detection_result(video_path)  # Call detection function
            print("RESULT***********: ", result)
            if result:
                return render(request, "main/real.html", {"form": form, "result": result})
            else:
                return render(request, "main/real.html", {"form": form, "result": "No result"})
    else:
        form = VerifyForm()
    return render(request, "main/real.html", {"form": form})
