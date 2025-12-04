# ISSC-Django

## Dependencies
Download FFMPEG [Here](https://github.com/BtbN/FFmpeg-Builds/releases)
**ffmpeg-master-latest-win64-gpl**

Download wkhtmltopdf [Here](https://wkhtmltopdf.org/downloads.html) for Windows


## Reinstall Packages

### Install via pip
Run the following commands to install the necessary packages:

```bash
pip install deepface==0.0.93 easyocr==1.7.2 h5py==3.12.1 imageio==2.37.0 Keras-Preprocessing==1.1.2 matplotlib==3.10.0 opencv-contrib-python==4.5.5.64 opencv-python==4.5.5.64 opencv-python-headless==4.10.0.84 pandas==2.2.3 retina-face==0.0.17 roboflow==1.1.54 scikit-image==0.25.1 argon2-cffi
```

run this next

```bash
pip install numpy==1.23.5 django mysqlclient tensorflow==2.10.0 whitenoise
```

```bash
pip install pdfkit
pip install openpyxl
```

## env
```.env
### API KEY
SECRET_KEY          = ""
### Database Credentials
DB_NAME             = ""
DB_USER             = ""
DB_PASSWORD         = ""
DB_HOST             = ""
DB_PORT             = ""

### Model
ROBOFLOW_API_KEY    = ""
PROJECT_NAME        = "issc-plate-recognition"

### SMTP
EMAIL_HOST_USER     = ""
EMAIL_HOST_PASSWORD = ""
```
# Code Review

## Structure

```bash
E:.
├── manage.py
├── issc
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── __init__.py
├── main
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   ├── __init__.py
│   ├── computer_vision
│   │   ├── face_enrollment.py
│   │   ├── plate_recognition.py
│   ├── migrations
│   ├── static
│   │   ├── css
│   │   │   ├── about.css
│   │   │   ├── dashboard.css
│   │   │   ├── details.css
│   │   │   ├── face.css
│   │   │   ├── forms.css
│   │   │   ├── live-feed.css
│   │   │   ├── login.css
│   │   │   ├── recording_archive.css
│   │   │   ├── styles.css
│   │   ├── images
│   │       ├── background.jpg
│   │       ├── overlay-bg.jpg
│   │       ├── overlay-logo.jpg
│   │       ├── pup-logo.png
│   ├── templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── reset.html
│   │   ├── signup.html
│   │   ├── signup_form.html
│   │   ├── test.html
│   │   ├── about
│   │   │   ├── about.html
│   │   ├── Components
│   │   │   ├── admin_sidebar.html
│   │   │   ├── faculty_sidebar.html
│   │   │   ├── student_sidebar.html
│   │   ├── dashboard
│   │   │   ├── dashboard.html
│   │   ├── face_enrollment
│   │   │   ├── face.html
│   │   ├── incident
│   │   │   ├── details.html
│   │   │   ├── forms.html
│   │   │   ├── admin
│   │   │   │   ├── incident.html
│   │   │   ├── student
│   │   │       ├── incident.html
│   │   ├── live-feed
│   │   │   ├── live-feed.html
│   │   │   ├── recording_arcihve.html
│   │   ├── registration
│   │   │   ├── acc_reset.html
│   │   │   ├── acc_reset_complete.html
│   │   │   ├── acc_reset_confirm.html
│   │   │   ├── acc_reset_done.html
│   │   │   ├── acc_reset_email.html
│   │   ├── vehicle
│   │       ├── details.html
│   │       ├── forms.html
│   │       ├── admin
│   │       │   ├── vehicle.html
│   │       ├── student
│   │           ├── vehicle.html
│   ├── views
│   │   ├── about_view.py
│   │   ├── auth_view.py
│   │   ├── dashboard_view.py
│   │   ├── face_enrollment_view.py
│   │   ├── forms.py
│   │   ├── incident_view.py
│   │   ├── live_view.py
│   │   ├── utils.py
│   │   ├── vehicle_view.py
│   │   ├── video_feed_view.py
│   │  
└── recordings
```
### issc
- Stores App Settings
### settings.py
- `LOGIN_URL` - Redirect path when user is unauthenticated
- `MEDIA_ROOT` - storage for media files
- `RECORDING_ROOT` - stores live feed recording 
- `EMAIL_HOST` - email provider
- `EMAIL_HOST_USER` - email address
- `EMAIL_HOST_PASSWORD` - email app password

### main
- store main functionality
- `urls.py` - stores paths
#### views
- stores page functionality
##### `video_feed_view.py`
- Load Conputer Vision Model
```python
recognizer = LicencePlateRecognition(os.getenv("ROBOFLOW_API_KEY"), os.getenv("PROJECT_NAME"), "1")
```

- Initialize cameras and frames
```python
NUM_CAMERAS = 4
cameras = {i: cv2.VideoCapture(i) for i in range(NUM_CAMERAS)}
frame_queues = {i: Queue(maxsize=10) for i in cameras}
```

- initialize video recording for each camera
```python
def initialize_video_writers():
    """Creates new video writers for each camera."""
    global video_writers
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    new_video_writers = {}

    for cam_id in cameras:
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_FORMAT)
        video_path = os.path.join(SAVE_DIR, f'camera_{cam_id}_{date_str}.avi')
        new_video_writers[cam_id] = cv2.VideoWriter(video_path, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))

    video_writers = new_video_writers  # Replace old video writers
```

- start and stop recording
```python
def start_record(request):
    global recording
    if recording:
        return redirect('multiple_streams')
    else:
        recording = True
        initialize_video_writers()
        return redirect('multiple_streams')

def stop_record(request):
    global recording
    if recording:
        recording = False
        global video_writers

        # Release current video writers
        for cam_id in video_writers:
            video_writers[cam_id].release()
        recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
        reencode_avi_to_mp4(recordings_dir)

        return redirect('multiple_streams')

    else:
        return redirect('multiple_streams')
```

- process frame to detect and recognize plate
```python
def process_with_model(frame):
    """Processes a video frame to detect and recognize license plates efficiently."""
    
    bounding_boxes = recognizer.detect_license_plate(frame)
    
    if not bounding_boxes:
        return frame  

    cropped_plates = recognizer.crop_license_plate(frame, bounding_boxes)
    plate_texts = recognizer.recognize_text(cropped_plates) if cropped_plates else []
    
    for (box, text) in zip(bounding_boxes, plate_texts):
        x_min, y_min, x_max, y_max = box
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
        
        cv2.putText(frame, text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.9, (0, 0, 255), 2, cv2.LINE_AA)

    return frame
```


- capture frames
```python
def capture_frames(camera_id):
    """Captures frames and skips unnecessary processing to speed up inference."""
    global frame_count
    cap = cameras[camera_id]

    while running:
        success, frame = cap.read()
        if not success:
            frame = generate_no_signal_frame()

        frame_count += 1
        # if frame_count % FRAME_SKIP == 0:  # Only process every 5th frame
            # frame = process_with_model(frame)

        if not frame_queues[camera_id].full():
            frame_queues[camera_id].put(frame)

        if camera_id in video_writers:
            video_writers[camera_id].write(frame)

        time.sleep(1/FPS)
```

- start threading for each camera
```python
for cam_id in cameras:
    Thread(target=capture_frames, args=(cam_id,), daemon=True).start()

```


- stream cameras
```python
def video_feed(request, camera_id):
    """Serves the video feed for a given camera."""
    camera_id = int(camera_id)

    if camera_id not in cameras:
        return HttpResponse(f"Camera {camera_id} not found", status=404)

    return StreamingHttpResponse(generate(camera_id), content_type='multipart/x-mixed-replace; boundary=frame')

def multiple_streams(request):
    """Renders a page with multiple camera streams."""
    user = AccountRegistration.objects.filter(username=request.user).values()
    template = loader.get_template('live-feed/live-feed.html')

    context = {
        'user_role': user[0]['privilege'],
        'user_data': user[0],
        'camera_ids': list(cameras.keys())
    }
    return HttpResponse(template.render(context, request))
```

- reset camera and reencode feed
```python
def reset_recordings(request):
    """Stops current video recording and starts a new one for each camera."""
    global video_writers

    # Release current video writers
    for cam_id in video_writers:
        video_writers[cam_id].release()



    recordings_dir = os.path.join(settings.BASE_DIR, 'recordings')
    reencode_avi_to_mp4(recordings_dir)

    # Create new video writers
    initialize_video_writers()

    return redirect('recording_archive')
```

- format reencode function using ffmpeg
```python
def reencode_avi_to_mp4(directory):
    """Searches for all .avi files in the specified directory, converts them to .mp4 using ffmpeg, and deletes the original .avi files."""
    
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    for filename in os.listdir(directory):
        if filename.endswith(".avi"):
            avi_path = os.path.join(directory, filename)
            mp4_path = os.path.join(directory, filename.replace(".avi", ".mp4"))
            
            print(f"Converting {avi_path} to {mp4_path}...")
            
            # FFmpeg command for re-encoding AVI to MP4 (H.264 codec)
            command = [
                "ffmpeg",
                "-i", avi_path,         # Input file
                "-c:v", "libx264",      # Video codec
                "-preset", "fast",      # Encoding speed
                "-crf", "23",           # Quality (lower is better, 23 is default)
                "-c:a", "aac",          # Audio codec
                "-b:a", "128k",         # Audio bitrate
                mp4_path                # Output file
            ]
            
            try:
                subprocess.run(command, check=True)
                print(f"Successfully converted {avi_path} to {mp4_path}")

                # Delete the original .avi file
                os.remove(avi_path)
                print(f"Deleted original file: {avi_path}")

            except subprocess.CalledProcessError as e:
                print(f"Error converting {avi_path}: {e}")
```

# Face and License Plate Recognition Section

This repository provides two Python modules for face enrollment and license plate recognition. It utilizes OpenCV, DeepFace, Roboflow, and EasyOCR for image processing and recognition tasks.

## Features

### 1. Face Enrollment Module
- Detects faces in an image using OpenCV's Haar cascade classifier.
- Generates face embeddings using DeepFace with a configurable model.
- Supports batch processing of multiple face images.

### 2. License Plate Recognition Module
- Detects license plates using a Roboflow-trained model.
- Crops detected plates from video frames.
- Extracts text from license plates using EasyOCR with preprocessing steps.

---

## Usage

### Face Enrollment

```python
import cv2
from face_enrollment import FaceEnrollment

# Initialize face enrollment
face_enroller = FaceEnrollment(model_name='Facenet')

# Load an image
image = cv2.imread("face.jpg")

# Detect faces
faces = face_enroller.detect_faces(image)

# Get embeddings for detected faces
for (x, y, w, h, face) in faces:
    embedding = face_enroller.get_face_embedding(face)
    print(embedding)
```

### License Plate Recognition

```python
import cv2
from licence_plate_recognition import LicencePlateRecognition

# Initialize license plate recognizer
lpr = LicencePlateRecognition("your_roboflow_api_key", "model_name", "model_version")

# Load an image
frame = cv2.imread("car.jpg")

# Detect license plates
plates = lpr.detect_license_plate(frame)

# Crop detected plates
cropped_plates = lpr.crop_license_plate(frame, plates)

# Recognize text from cropped plates
texts = lpr.recognize_text(cropped_plates)
print(texts)
```

---

## Configuration

- **FaceEnrollment** supports multiple models (e.g., 'Facenet', 'VGG-Face', 'OpenFace'). Modify the `model_name` parameter accordingly.
- **LicencePlateRecognition** requires a Roboflow API key and model details for plate detection. Adjust `DOWNSCALE_FACTOR` for performance tuning.

---
