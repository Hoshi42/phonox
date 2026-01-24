# Frontend Testing Guide - Phonox

## ✅ Current Status

Both servers are now running:

### Backend Server
- **URL**: http://localhost:8000
- **Status**: ✅ Running on port 8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **Log File**: `backend.log`

### Frontend Server
- **URL**: http://localhost:5173
- **Status**: ✅ Running on port 5173
- **Hot Reload**: Enabled (changes auto-refresh)

---

## 🧪 Testing Steps

### Option 1: Manual Testing (Browser)

1. **Open Frontend**
   ```
   http://localhost:5173
   ```

2. **Test Image Upload**
   - Click on the upload area or drag-and-drop
   - Select 1-5 PNG/JPG images from your computer
   - You should see image previews
   - Click "Upload" button

3. **Watch Results**
   - Loading spinner appears while analyzing
   - Results display with:
     - Artist, Title, Year, Label, Catalog #, Genres
     - Confidence score (0-100%)
     - Auto-approved or needs-review badge

4. **Submit Corrections (if low confidence)**
   - Fill in any corrections
   - Click "Submit Corrections"
   - See updated results

5. **Test Again**
   - Click "Identify Another Record"
   - Repeat with different images

---

### Option 2: Automated E2E Testing (Playwright)

1. **Run Playwright Tests**
   ```bash
   cd frontend
   npm run test:e2e
   ```

2. **Expected Output**
   ```
   ✓ 13 tests passing
   ```

3. **Run with UI (Visual Mode)**
   ```bash
   npm run test:e2e:ui
   ```
   This opens an interactive test viewer.

---

### Option 3: Manual API Testing

1. **Health Check**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Root Endpoint**
   ```bash
   curl http://localhost:8000/
   ```

3. **Upload Images** (requires actual image file)
   ```bash
   curl -X POST http://localhost:8000/api/v1/identify \
     -F "image_0=@/path/to/image1.jpg" \
     -F "image_1=@/path/to/image2.jpg"
   ```

4. **Get Results**
   ```bash
   # Use the record_id from the upload response
   curl http://localhost:8000/api/v1/identify/{record_id}
   ```

5. **Submit Review**
   ```bash
   curl -X POST http://localhost:8000/api/v1/identify/{record_id}/review \
     -H "Content-Type: application/json" \
     -d '{"artist":"Your Correction","title":"Album Name"}'
   ```

---

## 📝 What to Look For

### ✅ Successful Upload Flow
- [ ] Images upload without errors
- [ ] Spinner shows while processing
- [ ] Results display after 15-30 seconds
- [ ] Metadata shows (artist, title, etc.)
- [ ] Confidence score displays correctly

### ✅ Confidence Indicators
- [ ] Green color for ≥85% confidence
- [ ] Orange color for 60-84% confidence
- [ ] Red color for <60% confidence
- [ ] "Auto-Approved" badge appears for high confidence

### ✅ Manual Review
- [ ] Review form shows for low confidence
- [ ] Form fields are editable
- [ ] Submit sends corrections to backend
- [ ] Results update after submission

### ✅ Error Handling
- [ ] Error message displays on upload failure
- [ ] User can dismiss errors and try again
- [ ] No console errors in browser DevTools

### ✅ Mobile Responsiveness
- [ ] Press F12 in browser
- [ ] Toggle device toolbar (or Ctrl+Shift+M)
- [ ] Select "Mobile" device
- [ ] Test upload and form on mobile screen

---

## 🔧 Troubleshooting

### Frontend won't load?
```bash
# Check if Vite is running
curl http://localhost:5173
```

### Backend not responding?
```bash
# Check backend status
curl http://localhost:8000/health

# View logs
tail -20 backend.log
```

### Images not uploading?
1. Ensure backend is running (`curl http://localhost:8000/health`)
2. Open browser DevTools (F12)
3. Check Network tab for failed requests
4. Check Console tab for JavaScript errors

### E2E tests failing?
```bash
# Run with more details
npm run test:e2e -- --debug

# Run specific test
npm run test:e2e -- -g "upload"
```

---

## 📊 Test Results

When everything works:

```
Frontend: ✅ Loads on http://localhost:5173
Backend:  ✅ Responds on http://localhost:8000
Upload:   ✅ Images accepted and processed
Results:  ✅ Display with confidence scores
Review:   ✅ Corrections can be submitted
E2E:      ✅ All 13 tests pass
```

---

## 🎯 Test Scenarios

### Scenario 1: Quick Test (5 minutes)
1. Open http://localhost:5173
2. Upload 1-2 images
3. Wait for results
4. Verify display and confidence score

### Scenario 2: Full Workflow (15 minutes)
1. Upload images (1-5)
2. Wait for high confidence results
3. Note the auto-approved badge
4. Click "Identify Another Record"
5. Upload different images
6. Get low confidence results
7. Fill in manual corrections
8. Submit corrections
9. Verify updated results

### Scenario 3: Mobile Test (10 minutes)
1. Press F12 to open DevTools
2. Toggle device toolbar
3. Select mobile device
4. Resize window
5. Test upload flow on mobile
6. Verify responsive design

### Scenario 4: E2E Automated Test (5 minutes)
1. Run `npm run test:e2e`
2. View test report
3. Check HTML report: `frontend/playwright-report/index.html`

---

## 📱 Sample Images

To test without real vinyl records, you can:

1. **Use existing images**: Any PNG/JPG file works (test images)
2. **Create sample images**: 
   ```bash
   # Create a 500x500 test image
   python3 -c "from PIL import Image; Image.new('RGB', (500, 500), color='red').save('test.jpg')"
   ```
3. **Download samples**: Search for "vinyl record" images online

---

## 🎨 Frontend Features to Test

- [x] Image preview grid
- [x] Drag-and-drop upload
- [x] File input validation (1-5 images)
- [x] Loading spinner animation
- [x] Confidence visualization
- [x] Metadata display
- [x] Auto-approved badge
- [x] Review form with validation
- [x] Error message display
- [x] "Reset" button functionality
- [x] Responsive design
- [x] Service worker registration

---

## 📚 Next Steps After Testing

After confirming everything works:

1. **Verify Backend Tests**
   ```bash
   pytest tests/ -v
   ```

2. **Check Type Safety**
   ```bash
   mypy backend/ --ignore-missing-imports
   ```

3. **Run E2E Tests**
   ```bash
   cd frontend && npm run test:e2e
   ```

4. **Ready for Phase 5**
   - Error handling improvements
   - Performance optimization
   - Production deployment

---

## 🆘 Need Help?

1. Check browser console (F12 → Console)
2. Check browser network (F12 → Network)
3. View backend logs: `tail backend.log`
4. Check implementation files:
   - Frontend: `frontend/src/`
   - Backend: `backend/`
   - Tests: `tests/`

---

**Happy testing! 🚀**
