# 🎯 READY TO TEST - Phonox Frontend

## ✅ Setup Complete

Both servers are now running and ready for testing:

```
Frontend: http://localhost:5173 ✅
Backend:  http://localhost:8000 ✅
```

---

## 🚀 Quick Start Testing

### **Step 1: Open Frontend in Browser**

Navigate to: **http://localhost:5173**

You should see:
- **Phonox - Vinyl Record Identifier** title
- Tagline: "Upload images of your vinyl records for AI-powered identification"
- **Image Upload Area** with drag-and-drop support

---

### **Step 2: Upload Images**

Choose one of these options:

**Option A: Drag & Drop**
1. Drag 1-5 image files onto the upload area
2. Click the upload area or drag files over it
3. You'll see image previews appear

**Option B: Click to Browse**
1. Click on the upload area
2. Select 1-5 PNG/JPG files from your computer
3. Click "Open"
4. You'll see image previews

**Note**: The system accepts 1-5 images at a time

---

### **Step 3: Submit Upload**

1. Click the **"Upload [X] Image(s)"** button
2. You'll see a **Loading Spinner** with message: "Analyzing vinyl records..."
3. Processing takes 15-30 seconds

---

### **Step 4: View Results**

After processing completes, you'll see:

```
✓ Artist:        [Detected artist name]
✓ Title:         [Album title]
✓ Year:          [Release year]
✓ Label:         [Record label]
✓ Catalog #:     [Catalog number]
✓ Genres:        [Genre tags]
✓ Confidence:    [Score with visual bar]
```

The result includes:
- **Auto-Approved Badge** (if confidence ≥ 85%)
- **Review Badge** (if confidence < 85%)
- **Color-coded confidence bar**:
  - 🟢 Green: ≥85% confidence (auto-approved)
  - 🟠 Orange: 60-84% (review recommended)
  - 🔴 Red: <60% (manual review required)

---

### **Step 5: Manual Review (if needed)**

If confidence is low, you'll see a **Review Form**:

1. **Correct any fields**:
   - Artist name
   - Album title
   - Release year
   - Label
   - Catalog number
   - Genres (comma-separated)
   - Additional notes

2. **Click "Submit Corrections"**

3. **See updated results** with your corrections applied

---

### **Step 6: Identify Another Record**

1. Click **"Identify Another Record"** button
2. Upload different images
3. Repeat the process

---

## 🧪 What to Test

### ✅ Upload Functionality
- [ ] Drag and drop works
- [ ] Click upload works
- [ ] File preview shows
- [ ] Error if <1 or >5 images
- [ ] Upload button enabled only with images selected

### ✅ Processing
- [ ] Loading spinner appears
- [ ] Processing message shows
- [ ] Spinner animates smoothly
- [ ] Results appear after ~20 seconds

### ✅ Results Display
- [ ] All metadata fields display
- [ ] Confidence bar shows percentage
- [ ] Color matches confidence level
- [ ] Badges display correctly
- [ ] "Auto-Approved" shows for high confidence
- [ ] "Needs Review" shows for low confidence

### ✅ Manual Review
- [ ] Form shows for low confidence
- [ ] All fields are editable
- [ ] Form validation works
- [ ] Submit button works
- [ ] Results update after submission

### ✅ User Interface
- [ ] Page title is centered
- [ ] Layout is clean and readable
- [ ] Buttons are clickable
- [ ] Colors are visually appealing
- [ ] Responsive design (resize window to test)

### ✅ Error Handling
- [ ] Upload errors show error message
- [ ] Error can be dismissed
- [ ] Can retry after error
- [ ] No JavaScript console errors (F12)

### ✅ Mobile Responsiveness
1. Press **F12** to open Developer Tools
2. Click **device icon** (or Ctrl+Shift+M)
3. Select **iPhone** or **Android** device
4. Test:
   - [ ] Layout adapts to screen
   - [ ] Touch interactions work
   - [ ] Buttons are tappable
   - [ ] Images display properly
   - [ ] Form is usable on mobile

---

## 🔍 Developer Testing

### Check Browser Console (F12)

1. Press **F12** to open DevTools
2. Click **Console** tab
3. Look for:
   - ✅ No red errors
   - ✅ Service worker registration message
   - ✅ API calls to backend

### Check Network Requests (F12 → Network)

1. Open DevTools (F12)
2. Click **Network** tab
3. Upload images
4. You should see:
   - ✅ `POST /api/v1/identify` - Returns 202 (accepted)
   - ✅ `GET /api/v1/identify/{id}` - Returns 200 (polling)

### Check Service Worker (F12 → Application)

1. Open DevTools (F12)
2. Click **Application** tab
3. Click **Service Workers** (left sidebar)
4. You should see:
   - ✅ Service worker listed
   - ✅ Status: "activated and running"

---

## 🐛 Troubleshooting

### Frontend won't load?
```bash
# Kill existing processes
pkill -f "npm run dev"

# Restart frontend
cd /home/hoshhie/phonox/frontend
npm run dev
```

### Backend not responding?
```bash
# Check backend status
curl http://localhost:8000/health

# Check logs
tail -20 /home/hoshhie/phonox/backend.log

# Restart if needed
pkill -f "uvicorn"
cd /home/hoshhie/phonox
nohup uvicorn backend.main:app --reload &
```

### Images won't upload?
1. **Check backend is running**: `curl http://localhost:8000/health`
2. **Check browser console**: F12 → Console for errors
3. **Check network tab**: F12 → Network → Look for failed requests
4. **Try with different images**: Some formats might not work

### E2E Tests failing?
```bash
cd /home/hoshhie/phonox/frontend
npm run test:e2e -- --debug
```

---

## 📊 Test Scenarios

### Quick Test (5 minutes)
1. Open http://localhost:5173
2. Upload 1 image
3. Wait for results (~20 sec)
4. Verify confidence score displays
5. Close browser

### Full Flow Test (15 minutes)
1. Upload images with high confidence record
2. Verify auto-approved badge
3. Click "Identify Another Record"
4. Upload low confidence record
5. Fill review form
6. Submit corrections
7. Verify results updated
8. Test on mobile view

### E2E Test (5 minutes)
```bash
cd /home/hoshhie/phonox/frontend
npm run test:e2e
```
Expected: All 13 tests pass ✅

---

## 📱 Using Test Images

If you don't have vinyl record images:

### Option 1: Use Any Images
- PNG, JPG files work
- Size: Any (recommended 500x500 or larger)
- Content: Doesn't have to be vinyl records

### Option 2: Download Samples
- Search "vinyl record" on Google Images
- Download a few samples
- Use for testing

### Option 3: Create Test Image
```bash
# Create a simple test image (requires PIL)
python3 << 'EOF'
from PIL import Image
img = Image.new('RGB', (500, 500), color='blue')
img.save('test_image.jpg')
print("Created: test_image.jpg")
EOF
```

---

## 🎯 Success Criteria

You'll know everything is working when:

✅ **Upload works** - Images upload without errors  
✅ **Loading shows** - Spinner appears while processing  
✅ **Results display** - Metadata, confidence, badges show  
✅ **Review works** - Can submit corrections  
✅ **Responsive** - Works on mobile view  
✅ **No errors** - Browser console is clean  
✅ **E2E passes** - All 13 Playwright tests pass  

---

## 📚 Next Steps

After confirming everything works:

1. **Run all backend tests**
   ```bash
   pytest tests/ -v
   ```

2. **Run E2E tests**
   ```bash
   cd frontend && npm run test:e2e
   ```

3. **Check type safety**
   ```bash
   mypy backend/ --ignore-missing-imports
   ```

4. **View full test report**
   ```bash
   open frontend/playwright-report/index.html
   ```

---

## 🆘 Need Help?

1. **Check logs**:
   ```bash
   tail backend.log          # Backend logs
   cat /tmp/vite.log        # Frontend logs
   ```

2. **Open browser DevTools**: F12
   - Console tab for errors
   - Network tab for API calls
   - Application tab for service worker

3. **Check documentation**:
   - `FRONTEND_TESTING.md` - Detailed testing guide
   - `frontend/README.md` - Frontend setup guide
   - `PROJECT_STATUS.md` - Project overview

---

## 🎉 Ready to Go!

Everything is set up and running. **Open your browser and visit:**

### **→ http://localhost:5173**

**Happy testing!** 🚀

---

**Servers Running**:
- Frontend: http://localhost:5173 ✅
- Backend: http://localhost:8000 ✅
- API Docs: http://localhost:8000/docs ✅

**Time to Start**: NOW!
