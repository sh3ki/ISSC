# 🧪 TESTING GUIDE - Face Recognition System

## ✅ Pre-Testing Checklist

Before testing, ensure:
- [ ] Django server is running: `python manage.py runserver`
- [ ] Database is migrated: `python manage.py migrate`
- [ ] At least one camera is connected
- [ ] Browser has camera permissions enabled
- [ ] Chrome/Edge browser (recommended for best compatibility)

---

## 📝 Test 1: Face Enrollment (3-Pose Capture)

### Steps:
1. Navigate to: `http://localhost:8000/face-enrollment/{id_number}/`
   - Replace `{id_number}` with a valid user ID from database

2. **Select Camera:**
   - Click dropdown "Select Camera"
   - Choose your camera (usually "Camera 0" for built-in)
   - Click "Initialize Camera"
   - Wait for video feed to appear

3. **Capture Front Face:**
   - Look straight at camera
   - Center your face in frame
   - Click "Capture Front" button
   - ✅ **Expected:** Green bounding box appears, image captured

4. **Capture Left Tilt:**
   - Turn head ~30° to the LEFT
   - Button changes to "Capture Left"
   - Click button
   - ✅ **Expected:** Different pose captured with bounding box

5. **Capture Right Tilt:**
   - Turn head ~30° to the RIGHT  
   - Button changes to "Capture Right"
   - Click button
   - ✅ **Expected:** Third pose captured

6. **Submit:**
   - Click "Enroll / Submit" button
   - ✅ **Expected:** Redirect to success page
   - ✅ **Expected:** Console shows "Embeddings saved successfully"

### Validation:
Check database:
```python
python manage.py shell
>>> from main.models import FacesEmbeddings
>>> embeddings = FacesEmbeddings.objects.all()
>>> for e in embeddings:
...     print(f"ID: {e.id_number.id_number}")
...     print(f"Has front: {bool(e.front_embedding)}")
...     print(f"Has left: {bool(e.left_embedding)}")
...     print(f"Has right: {bool(e.right_embedding)}")
```

✅ **PASS Criteria:**
- All 3 embeddings saved (front, left, right)
- Each embedding has 128 values
- Success page displayed

❌ **FAIL Indicators:**
- "Exactly one face must be detected" error
- Missing embeddings in database
- Same image captured 3 times

---

## 📝 Test 2: Live Feed Recognition (GREEN/RED Boxes)

### Steps:

#### Test 2A: Enrolled User (GREEN BOX)
1. Navigate to: `http://localhost:8000/live-feed/`

2. Stand in front of Camera 0 (or any camera)

3. Wait 1-2 seconds for detection

4. ✅ **Expected Results:**
   - 🟢 **GREEN bounding box** appears around face
   - Label shows: "✓ AUTHORIZED"
   - Your name appears below box
   - ID number shown
   - Confidence percentage displayed

5. **Console Output:**
   ```
   🔍 Face matching - ID: 12345, Confidence: 0.87
   ✅ AUTHORIZED - ID: 12345 (Confidence: 0.87)
   🟢 GREEN BOX - John Doe
   ```

#### Test 2B: Unauthorized User (RED BOX)
1. Have someone NOT enrolled stand in front of camera

2. Wait 1-2 seconds for detection

3. ✅ **Expected Results:**
   - 🔴 **RED bounding box** appears around face
   - Label shows: "✗ UNAUTHORIZED"
   - Text below shows: "Unknown Person"
   - No name or ID displayed

4. **Console Output:**
   ```
   🔍 Face matching - ID: None, Confidence: 0.23
   🔴 RED BOX - UNAUTHORIZED (Confidence: 0.23)
   ```

#### Test 2C: Multiple Faces
1. Have 2-3 people (mix of enrolled and not enrolled) stand in front of camera

2. ✅ **Expected Results:**
   - Separate bounding box for EACH face
   - Enrolled faces: 🟢 GREEN boxes
   - Unknown faces: 🔴 RED boxes
   - All boxes display simultaneously

### Validation:
- [ ] Enrolled faces always get GREEN boxes
- [ ] Unknown faces always get RED boxes
- [ ] Name displays correctly for enrolled faces
- [ ] No flickering of boxes
- [ ] Boxes track faces smoothly
- [ ] System handles 1-5+ faces

---

## 📝 Test 3: Enrollment Verification

### After enrolling, verify embeddings are loaded:

1. Navigate to: `http://localhost:8000/api/verify-face-embeddings/`

2. ✅ **Expected Response:**
```json
{
  "success": true,
  "database_embeddings": 5,
  "loaded_embeddings": 5,
  "embeddings_match": true,
  "embedding_details": [
    {
      "id_number": "12345",
      "first_name": "John",
      "last_name": "Doe",
      "has_front": true,
      "has_left": true,
      "has_right": true
    }
  ]
}
```

✅ **PASS:** `loaded_embeddings` matches `database_embeddings`
❌ **FAIL:** Numbers don't match → restart Django server

---

## 📝 Test 4: Performance Testing

### Test Frame Rate:
1. Open live feed page
2. Check browser console for FPS
3. ✅ **Expected:** 10-20 FPS
4. ❌ **Slow:** < 5 FPS → reduce camera resolution

### Test Recognition Speed:
1. Time from face appearing to box showing
2. ✅ **Expected:** < 1 second
3. ❌ **Slow:** > 2 seconds → check GPU acceleration

### Console Test:
```python
python manage.py shell
>>> from main.computer_vision.face_matching import FaceMatcher
>>> matcher = FaceMatcher(use_gpu=True)
>>> matcher.load_embeddings()
>>> print(f"Loaded {len(matcher.embeddings)} embeddings")
```

✅ **PASS:** Shows count of enrolled users
❌ **FAIL:** Shows 0 → check database

---

## 📝 Test 5: Edge Cases

### Test 5A: Poor Lighting
- Test in dim lighting
- ✅ **Expected:** Face still detected, may show RED if unclear
- 💡 **Tip:** Add more light for better accuracy

### Test 5B: Partial Face
- Cover half your face with hand
- ✅ **Expected:** May not detect face, or RED box if detected
- This is normal - system requires full face view

### Test 5C: Different Angles
- Turn head more than 45°
- ✅ **Expected:** Should still match if one angle (front/left/right) is visible
- This is why we capture 3 poses!

### Test 5D: Glasses/Accessories
- Wear glasses, hat, scarf
- ✅ **Expected:** Should still match if face features are visible
- ❌ **May fail:** if face is heavily obscured

### Test 5E: Distance from Camera
**Close (< 1 foot):**
- ✅ **Expected:** Face detected but may be too large

**Optimal (2-4 feet):**
- ✅ **Expected:** Best detection and matching

**Far (> 8 feet):**
- ✅ **Expected:** Face too small, may not detect

---

## 🔧 Troubleshooting During Testing

### Problem: No green box ever appears
**Solution:**
1. Check embeddings saved:
   ```python
   python manage.py shell
   >>> from main.models import FacesEmbeddings
   >>> FacesEmbeddings.objects.count()
   ```
2. Reload embeddings:
   - Restart Django server
   - Or navigate to enrollment page (triggers reload)

### Problem: All faces show red
**Solution:**
1. Lower threshold in `enhanced_video_feed.py` line ~603:
   ```python
   match_id, confidence = self.matcher.match(embedding, threshold=0.4)
   ```

### Problem: Wrong person matched
**Solution:**
1. Increase threshold for stricter matching:
   ```python
   match_id, confidence = self.matcher.match(embedding, threshold=0.3)
   ```

### Problem: System is slow
**Solution:**
1. Reduce frame skip in `enhanced_video_feed.py` line ~39:
   ```python
   self.FRAME_SKIP = 6  # Process every 6th frame instead of 4
   ```

### Problem: Boxes are flickering
**Solution:**
- Already implemented smoothing
- If still flickering, increase smoothing buffer in line ~764:
  ```python
  if len(self._stable_boxes[camera_id]) > 5:  # Keep 5 frames instead of 3
  ```

---

## 📊 Expected Test Results Summary

| Test | Pass Criteria | Typical Result |
|------|--------------|----------------|
| Enrollment | 3 poses saved | ✅ 10 sec total |
| Green Box (Enrolled) | Shows immediately | ✅ < 1 sec |
| Red Box (Unknown) | Shows immediately | ✅ < 1 sec |
| Multiple Faces | All detected | ✅ 2-5 faces |
| FPS | Smooth playback | ✅ 15-20 FPS |
| Accuracy | Correct matches | ✅ 95%+ |

---

## 🎯 Success Indicators

Your system is working correctly if:
- ✅ Enrollment completes in < 15 seconds
- ✅ Enrolled faces get GREEN boxes immediately
- ✅ Unknown faces get RED boxes immediately
- ✅ Names display correctly for enrolled users
- ✅ System handles multiple faces
- ✅ Live feed runs smoothly (10+ FPS)
- ✅ No system crashes or errors

---

## 📞 If All Tests Pass

**CONGRATULATIONS! 🎉**

Your face recognition system is:
- ✅ FULLY FUNCTIONAL
- ✅ FAST
- ✅ ACCURATE
- ✅ READY FOR PRODUCTION

**Next Steps:**
1. Enroll all users
2. Configure cameras for optimal coverage
3. Set appropriate thresholds for your use case
4. Monitor logs for any issues

---

## 📞 If Tests Fail

1. Check Django console for errors
2. Verify camera permissions
3. Ensure database migrations are current
4. Test with single camera first
5. Check if embeddings are loading (console logs)
6. Try lowering/raising threshold

**Common Issues:**
- Camera not found → Check connections
- No GREEN boxes → Check database embeddings
- Slow performance → Adjust FRAME_SKIP
- False matches → Lower threshold

---

**START TESTING NOW! 🚀**
