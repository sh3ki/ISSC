import cv2
import numpy as np
import easyocr

DOWNSCALE_FACTOR = 0.8  # Reduce resolution for Roboflow speed

class LicencePlateRecognition:
    def __init__(self, roboflow_api_key=None, model_name=None, model_version=None, use_haar=False):
        """
        Initialize the license plate recognizer with either a Roboflow model or Haar cascade.
        """
        self.use_haar = use_haar
        self.reader = easyocr.Reader(['en'])

        # Default to Haar cascade to avoid heavy external dependencies
        self.model = None
        self.plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')

    def detect_license_plate(self, frame):
        """
        Detect license plates using either Roboflow or Haar cascade.
        Returns bounding boxes [(x_min, y_min, x_max, y_max), ...]
        """
        plates = []
        if self.use_haar:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detections = self.plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
            for (x, y, w, h) in detections:
                plates.append((x, y, x + w, y + h))
        else:
            small_frame = cv2.resize(frame, (0, 0), fx=DOWNSCALE_FACTOR, fy=DOWNSCALE_FACTOR)
            response = self.model.predict(small_frame, confidence=40, overlap=30).json()
            for pred in response.get('predictions', []):
                x_min, y_min, x_max, y_max = [int(p / DOWNSCALE_FACTOR) for p in
                                              (pred['x'] - pred['width'] / 2, pred['y'] - pred['height'] / 2,
                                               pred['x'] + pred['width'] / 2, pred['y'] + pred['height'] / 2)]
                plates.append((x_min, y_min, x_max, y_max))
        return plates

    def crop_license_plate(self, frame, bounding_boxes):
        """Crop detected license plates from a video frame."""
        return [frame[y1:y2, x1:x2] for (x1, y1, x2, y2) in bounding_boxes]

    def recognize_text(self, cropped_images):
        """Extract text from cropped plate images using EasyOCR."""
        texts = []
        for img in cropped_images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            _, thresh = cv2.threshold(denoised, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = ' '.join(self.reader.readtext(thresh, detail=0))
            texts.append(text)
        return texts
