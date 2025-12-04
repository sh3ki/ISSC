# Camera Configuration

## Final Setup (October 1, 2025)

### Camera Assignment

| Frontend Display | Physical Camera Index | Camera Name | Description |
|-----------------|----------------------|-------------|-------------|
| Camera 0 | 1 | Acer HD user-facing camera | Built-in laptop camera |
| Camera 1 | 2 | Rapoo camera | External USB webcam with NVIDIA Broadcast |

### Physical Camera Detection

- **Physical Index 0**: Available (unused)
- **Physical Index 1**: Acer HD user-facing camera → Mapped to Frontend Camera 0
- **Physical Index 2**: Rapoo camera (NVIDIA Broadcast) → Mapped to Frontend Camera 1

### Key Implementation Details

1. **Rapoo Camera Handling**: 
   - Physical index 2 uses NVIDIA Broadcast software
   - Requires special handling - basic frame tests only (no extensive streaming tests)
   - Takes longer to initialize due to GPU processing

2. **Camera Detection**:
   - Scans physical indices 0, 1, and 2
   - Uses DirectShow (CAP_DSHOW) backend for best compatibility on Windows
   - Rapoo camera tries multiple backends for maximum compatibility

3. **Frontend Display**:
   - Camera 0 shows Acer HD (physical index 1)
   - Camera 1 shows Rapoo (physical index 2)
   - Both cameras support face detection and recording

### Code Changes Made

1. Updated `MAX_CAMERAS_TO_TRY` from 2 to 3 to scan physical index 2
2. Modified camera assignment in `initialize_live_feed_cameras()`:
   - `cameras[0] = new_cameras[1]` (Acer HD)
   - `cameras[1] = new_cameras[2]` (Rapoo)
3. Updated camera reinitialization logic to use correct physical indices
4. Removed excessive debug logging while keeping essential messages
5. Disabled streaming stability test for Rapoo camera (NVIDIA Broadcast sensitivity)

### Testing

Run the test script to verify cameras are detected:
```bash
python test_camera_indices.py
```

Expected output:
- Camera at index 1: ✅ Acer HD
- Camera at index 2: ✅ Rapoo (with NVIDIA Broadcast logs)

### Running the Server

```bash
cd issc
python manage.py runserver
```

Access the live feed at: `http://127.0.0.1:8000/live-feed/`

### Notes

- The Rapoo camera uses NVIDIA Broadcast which adds GPU-accelerated features
- Camera initialization may take slightly longer due to Broadcast software
- Both cameras support face detection, recognition, and recording features
- UI design and styling remain unchanged from original implementation
