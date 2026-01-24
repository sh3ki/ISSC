/**
 * ISSC Live Feed Face Recognition System
 * Carbon copy of PROTECH implementation WITHOUT spoofing detection
 * Supports multiple cameras with real-time face recognition
 */

const FACE_API_MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model';

class LiveFeedFaceRecognition {
    constructor(videoId, canvasId, cameraBoxId, fpsCounterId) {
        this.videoId = videoId;
        this.canvasId = canvasId;
        this.cameraBoxId = cameraBoxId;
        this.fpsCounterId = fpsCounterId;
        
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.isRunning = false;
        this.processingFrame = false;
        this.currentDetections = [];
        this.frameCount = 0;
        this.fps = 0;
        this.lastFpsUpdate = Date.now();
        this.recognitionCooldown = new Map();
        this.cooldownMs = 5000;  // 5 seconds cooldown per user
        this.resizeObserver = null;
        this.scaleX = 1;
        this.scaleY = 1;
        this.processIntervalMs = 500;  // Process every 500ms
        this.lastRecognitionTime = 0;
        this.lastResults = [];
        this.modelsLoaded = false;
        this.detectorOptions = null;
        this.unauthorizedCooldown = new Map();
        this.unauthorizedCooldownMs = 2000;
        
        // Track recognized users
        this.recognizedUsers = new Map();
    }

    async initialize() {
        try {
            // Support both video elements and img elements (for MJPEG streams)
            this.video = document.getElementById(this.videoId);
            this.canvas = document.getElementById(this.canvasId);

            if (!this.video || !this.canvas) {
                console.error(`[Camera ${this.cameraBoxId}] Video or canvas element not found.`);
                return;
            }

            // If video is actually an img element (MJPEG stream), we need to convert it
            if (this.video.tagName === 'IMG') {
                console.log(`[Camera ${this.cameraBoxId}] Converting IMG stream to video...`);
                this.isImageStream = true;
                this.imgElement = this.video;
                
                // Create a hidden video element
                this.video = document.createElement('video');
                this.video.autoplay = true;
                this.video.muted = true;
                this.video.playsInline = true;
                this.video.style.display = 'none';
                this.imgElement.parentElement.appendChild(this.video);
                
                // Start syncing image to video
                this.startImageToVideoSync();
            }

            this.ctx = this.canvas.getContext('2d', { alpha: true });
            if (!this.ctx) {
                console.error(`[Camera ${this.cameraBoxId}] Unable to obtain 2D canvas context.`);
                return;
            }

            await this.loadModels();
            if (!this.modelsLoaded) {
                console.error(`[Camera ${this.cameraBoxId}] face-api models failed to load.`);
                return;
            }

            this.registerVideoEvents();

            if (this.video.readyState >= 2 && !this.video.paused && !this.video.ended) {
                this.onVideoReady();
            }
            
            console.log(`[Camera ${this.cameraBoxId}] ✅ Face recognition initialized successfully.`);
        } catch (error) {
            console.error(`[Camera ${this.cameraBoxId}] Failed to initialize face recognition:`, error);
        }
    }

    startImageToVideoSync() {
        // Create canvas for converting image to video stream
        this.syncCanvas = document.createElement('canvas');
        this.syncCtx = this.syncCanvas.getContext('2d');
        
        const syncFrame = () => {
            if (!this.isRunning && !this.imgElement) {
                return;
            }
            
            try {
                if (this.imgElement && this.imgElement.complete && this.imgElement.naturalWidth > 0) {
                    this.syncCanvas.width = this.imgElement.naturalWidth;
                    this.syncCanvas.height = this.imgElement.naturalHeight;
                    this.syncCtx.drawImage(this.imgElement, 0, 0);
                    
                    // Convert canvas to video stream (only create once)
                    if (!this.video.srcObject) {
                        const stream = this.syncCanvas.captureStream(30); // 30 FPS
                        this.video.srcObject = stream;
                    }
                }
            } catch (error) {
                console.error(`[Camera ${this.cameraBoxId}] Error syncing image to video:`, error);
            }
            
            requestAnimationFrame(syncFrame);
        };
        
        syncFrame();
    }

    async loadModels() {
        if (this.modelsLoaded) {
            return;
        }

        if (typeof faceapi === 'undefined') {
            console.error(`[Camera ${this.cameraBoxId}] face-api.js is not available.`);
            return;
        }

        try {
            // Models are shared globally, so only load once
            if (!window.faceApiModelsLoaded) {
                console.log('Loading face-api models...');
                await Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri(FACE_API_MODEL_URL),
                    faceapi.nets.faceLandmark68Net.loadFromUri(FACE_API_MODEL_URL),
                    faceapi.nets.faceRecognitionNet.loadFromUri(FACE_API_MODEL_URL)
                ]);
                window.faceApiModelsLoaded = true;
                console.log('✅ face-api models loaded (shared).');
            }
            
            this.detectorOptions = new faceapi.TinyFaceDetectorOptions({
                inputSize: 224,
                scoreThreshold: 0.5
            });
            this.modelsLoaded = true;
            console.log(`[Camera ${this.cameraBoxId}] face-api models ready.`);
        } catch (error) {
            console.error(`[Camera ${this.cameraBoxId}] Error loading face-api models:`, error);
        }
    }

    registerVideoEvents() {
        const handleReady = () => this.onVideoReady();
        this.video.addEventListener('loadedmetadata', handleReady);
        this.video.addEventListener('play', handleReady);

        if (typeof ResizeObserver !== 'undefined') {
            this.resizeObserver = new ResizeObserver(() => this.syncCanvasSize());
            this.resizeObserver.observe(this.video);
        } else {
            window.addEventListener('resize', () => this.syncCanvasSize());
        }
    }

    onVideoReady() {
        if (!this.video.videoWidth || !this.video.videoHeight) {
            return;
        }

        this.syncCanvasSize();

        if (!this.isRunning) {
            this.isRunning = true;
            requestAnimationFrame(() => this.recognitionLoop());
            console.log(`[Camera ${this.cameraBoxId}] Face recognition loop started.`);
        }
    }

    syncCanvasSize() {
        if (!this.video.videoWidth || !this.video.videoHeight) {
            return;
        }

        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;

        const rect = this.video.getBoundingClientRect();
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.pointerEvents = 'none';

        this.scaleX = this.canvas.width / this.video.videoWidth;
        this.scaleY = this.canvas.height / this.video.videoHeight;
    }

    async recognitionLoop() {
        if (!this.isRunning) {
            return;
        }

        this.drawDetections();

        if (!this.processingFrame) {
            this.processingFrame = true;
            this.processFrame()
                .catch(error => console.error(`[Camera ${this.cameraBoxId}] Error processing frame:`, error))
                .finally(() => {
                    this.processingFrame = false;
                });
        }

        requestAnimationFrame(() => this.recognitionLoop());
    }

    drawDetections() {
        if (!this.ctx) {
            return;
        }

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        for (const detection of this.currentDetections) {
            if (detection.status === 'matched') {
                const result = detection.result || {};
                const lines = [];
                
                // Display full name
                const name = result.name || '';
                if (name) {
                    lines.push(name);
                }
                
                // Display ID number
                if (result.id_number) {
                    lines.push('ID: ' + result.id_number);
                }
                
                // Display confidence
                if (typeof result.confidence === 'number') {
                    lines.push('Confidence: ' + (result.confidence * 100).toFixed(1) + '%');
                }

                // GREEN bounding box for AUTHORIZED
                this.drawStyledBox(detection.box, {
                    stroke: '#22C55E',  // Green
                    fill: 'rgba(34, 197, 94, 0.25)',
                    labelLines: lines.length ? lines : ['Authorized'],
                    labelColor: '#000000'
                });
            } else {
                // RED bounding box for UNAUTHORIZED
                this.drawStyledBox(detection.box, {
                    stroke: '#EF4444',  // Red
                    fill: 'rgba(239, 68, 68, 0.25)',
                    labelLines: ['UNAUTHORIZED'],
                    labelColor: '#FFFFFF'
                });
            }
        }
    }

    drawStyledBox(box, options) {
        if (!box) {
            return;
        }

        const config = Object.assign({
            stroke: '#FFFFFF',
            fill: null,
            labelLines: [],
            labelColor: '#FFFFFF'
        }, options || {});

        const start = box.start || [0, 0];
        const end = box.end || [0, 0];

        const x1 = Math.max(0, Math.min(start[0], this.canvas.width));
        const y1 = Math.max(0, Math.min(start[1], this.canvas.height));
        const x2 = Math.max(0, Math.min(end[0], this.canvas.width));
        const y2 = Math.max(0, Math.min(end[1], this.canvas.height));

        const width = Math.max(0, x2 - x1);
        const height = Math.max(0, y2 - y1);

        this.ctx.save();

        if (config.fill) {
            this.ctx.fillStyle = config.fill;
            this.ctx.fillRect(x1, y1, width, height);
        }

        this.ctx.strokeStyle = config.stroke;
        this.ctx.lineWidth = 4;
        this.ctx.strokeRect(x1, y1, width, height);

        if (config.labelLines.length) {
            const lineHeight = 18;
            const padding = 8;
            const boxHeight = config.labelLines.length * lineHeight + padding * 2;
            const labelWidth = Math.max(width, 140);
            let labelTop = y1 - boxHeight - 4;
            if (labelTop < 0) {
                labelTop = y1 + 4;
            }

            this.ctx.fillStyle = config.stroke;
            this.ctx.fillRect(x1, labelTop, labelWidth, boxHeight);

            this.ctx.fillStyle = config.labelColor;
            this.ctx.font = 'bold 14px Arial';
            config.labelLines.forEach((line, index) => {
                this.ctx.fillText(line, x1 + padding, labelTop + padding + (index + 1) * lineHeight - 4);
            });
        }

        this.ctx.restore();
    }

    async processFrame() {
        if (!this.modelsLoaded || !this.video || this.video.readyState < 2) {
            return;
        }

        let detections = [];
        try {
            detections = await faceapi
                .detectAllFaces(this.video, this.detectorOptions)
                .withFaceLandmarks()
                .withFaceDescriptors();
        } catch (error) {
            console.error(`[Camera ${this.cameraBoxId}] face-api detection error:`, error);
            return;
        }

        if (!detections.length) {
            this.currentDetections = [];
            this.lastResults = [];
            this.updateFPS();
            return;
        }

        const boxes = detections.map(detection => {
            const box = detection.detection.box;
            return {
                start: [box.x * this.scaleX, box.y * this.scaleY],
                end: [(box.x + box.width) * this.scaleX, (box.y + box.height) * this.scaleY]
            };
        });

        const now = Date.now();
        const shouldRecognize = now - this.lastRecognitionTime >= this.processIntervalMs;

        let recognitionResults;

        if (shouldRecognize) {
            const descriptors = detections.map(det => Array.from(det.descriptor));
            const results = await this.recognizeFaces(descriptors);
            
            recognitionResults = this.normalizeResults(results, boxes.length);
            this.lastResults = recognitionResults;
            this.lastRecognitionTime = now;
        } else {
            recognitionResults = this.normalizeResults(this.lastResults, boxes.length);
        }

        this.currentDetections = boxes.map((box, index) => {
            const result = recognitionResults[index];
            const matched = result && result.matched;
            
            return {
                box: box,
                result: result,
                status: matched ? 'matched' : 'unknown'
            };
        });

        if (shouldRecognize) {
            for (const detection of this.currentDetections) {
                if (detection.status === 'matched') {
                    await this.recordFaceLog(detection.result);
                } else {
                    // Save unauthorized face
                    await this.saveUnauthorizedFace(detection);
                }
            }
        }

        this.updateFPS();
    }

    async recognizeFaces(faceEmbeddings) {
        if (!faceEmbeddings.length) {
            return [];
        }

        try {
            const response = await fetch('/api/recognize-faces/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ face_embeddings: faceEmbeddings })
            });

            if (!response.ok) {
                console.error(`[Camera ${this.cameraBoxId}] Recognition API error:`, response.status);
                return faceEmbeddings.map(() => ({ matched: false }));
            }

            const data = await response.json();
            if (data && data.success && Array.isArray(data.results)) {
                return data.results;
            }

            return faceEmbeddings.map(() => ({ matched: false }));
        } catch (error) {
            console.error(`[Camera ${this.cameraBoxId}] Error calling recognition API:`, error);
            return faceEmbeddings.map(() => ({ matched: false }));
        }
    }

    normalizeResults(results, expectedLength) {
        if (!Array.isArray(results)) {
            return new Array(expectedLength).fill(null).map(() => ({ matched: false }));
        }

        if (results.length !== expectedLength) {
            const padded = results.slice();
            while (padded.length < expectedLength) {
                padded.push({ matched: false });
            }
            return padded.slice(0, expectedLength);
        }

        return results;
    }

    async recordFaceLog(result) {
        const id_number = result && result.id_number;
        if (!id_number) {
            return;
        }

        // Check cooldown
        const lastTime = this.recognitionCooldown.get(id_number);
        const now = Date.now();
        if (lastTime && (now - lastTime) < this.cooldownMs) {
            return;
        }

        this.recognitionCooldown.set(id_number, now);

        try {
            const response = await fetch('/api/record-face-log/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id_number: id_number })
            });

            const data = await response.json();
            if (data.success && !data.is_duplicate) {
                console.log(`✅ [Camera ${this.cameraBoxId}] Face log recorded: ${result.name}`);
            }
        } catch (error) {
            console.error(`[Camera ${this.cameraBoxId}] Error recording face log:`, error);
        }
    }

    async saveUnauthorizedFace(detection) {
        const now = Date.now();
        const boxKey = `box_${this.cameraBoxId}`;
        
        const lastTime = this.unauthorizedCooldown.get(boxKey);
        if (lastTime && (now - lastTime) < this.unauthorizedCooldownMs) {
            return;
        }

        this.unauthorizedCooldown.set(boxKey, now);

        try {
            // Capture image from video
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = this.video.videoWidth;
            tempCanvas.height = this.video.videoHeight;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.drawImage(this.video, 0, 0);
            
            const imageData = tempCanvas.toDataURL('image/jpeg', 0.8);

            const response = await fetch('/api/save-unauthorized-face/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image: imageData,
                    camera_box_id: this.cameraBoxId
                })
            });

            const data = await response.json();
            if (data.success) {
                console.log(`⚠️ [Camera ${this.cameraBoxId}] Unauthorized face saved`);
            }
        } catch (error) {
            console.error(`[Camera ${this.cameraBoxId}] Error saving unauthorized face:`, error);
        }
    }

    updateFPS() {
        this.frameCount++;
        const now = Date.now();
        const elapsed = now - this.lastFpsUpdate;

        if (elapsed >= 1000) {
            this.fps = Math.round((this.frameCount * 1000) / elapsed);
            this.frameCount = 0;
            this.lastFpsUpdate = now;

            const fpsElement = document.getElementById(this.fpsCounterId);
            if (fpsElement) {
                fpsElement.textContent = `${this.fps} FPS`;
            }
        }
    }

    stop() {
        this.isRunning = false;
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
    }
}

// Global instances for each camera
window.faceRecognitionInstances = {};

// Initialize face recognition for a camera
function initializeFaceRecognition(videoId, canvasId, cameraBoxId, fpsCounterId) {
    const instance = new LiveFeedFaceRecognition(videoId, canvasId, cameraBoxId, fpsCounterId);
    instance.initialize();
    window.faceRecognitionInstances[cameraBoxId] = instance;
    return instance;
}
