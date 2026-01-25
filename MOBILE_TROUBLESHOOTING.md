# Mobile Troubleshooting Guide

## Issue: Register not loading on mobile despite API working

### Quick Fixes (Try these first):

#### 1. **Clear Mobile Browser Cache**
- **Chrome Mobile**: Settings → Privacy & Security → Clear browsing data → Check "Cached images and files" → Clear data
- **Safari Mobile**: Settings → Safari → Clear History and Website Data
- **Firefox Mobile**: Menu → Settings → Clear private data → Cache

#### 2. **Hard Reload on Mobile**
- **Chrome Mobile**: Pull down to refresh multiple times
- **Safari Mobile**: Hold refresh button → "Request Desktop Site" → Hold refresh again → "Request Mobile Site"

#### 3. **Use Mobile Debug Tool**
1. On mobile browser, navigate to: `http://YOUR_IP:3000/mobile-debug.html`
2. Click "Clear All Caches" 
3. Wait for page to reload automatically
4. Then navigate back to main app: `http://YOUR_IP:3000`

### Technical Improvements Made:

#### Service Worker Updates
- Removed aggressive caching that caused empty pages
- Added cache busting on user switches
- Service worker now updates when switching users

#### UserManager Enhanced 
- Added `Cache-Control: no-cache` headers to API calls
- Added cache timestamp `?_t=${Date.now()}` to prevent caching
- Forces service worker update on user change

#### Register API Enhanced
- Added cache busting parameters to register API calls  
- Added `no-cache` headers for mobile compatibility
- Register loading now forces fresh data fetch

#### Mobile-Specific Fixes
- Always-visible user buttons for mobile touch interface
- Proper touch targets (44px minimum)
- Enhanced mobile debug tool with cache management

### Debugging Steps:

#### Step 1: Check Network
Open mobile browser console and look for:
- API calls to `/register/users` and `/register/?user_tag=Jan`  
- Network errors or failed requests
- CORS errors

#### Step 2: Check Local Storage
In mobile browser console, run:
```javascript
localStorage.getItem('phonox_username')
// Should show: "Jan"
```

#### Step 3: Test API Directly  
In mobile browser, navigate to:
```
http://YOUR_IP:8000/register/users
http://YOUR_IP:8000/register/?user_tag=Jan
```

#### Step 4: Check Service Worker
In mobile browser console, run:
```javascript
navigator.serviceWorker.getRegistrations().then(regs => console.log(regs))
```

### Expected Behavior:
1. User switches to "Jan" → API call to `/register/?user_tag=Jan`
2. API returns: `[{"id":"1","artist":"Danzig","title":"Danzig",...}]`
3. UI shows 1 record in Jan's register
4. Register button shows "📚 My Register (1)"

### Common Mobile Issues:
- **Aggressive caching**: Mobile browsers cache more aggressively
- **Service Worker persistence**: Mobile keeps service workers longer
- **Memory management**: Mobile may not update state properly
- **Network switching**: Mobile switching between WiFi/cellular can cause issues

### Last Resort:
If nothing works:
1. Uninstall/reinstall mobile browser app
2. Clear all data for the domain in browser settings
3. Use a different mobile browser (Chrome, Firefox, Safari)
4. Connect mobile to same network as desktop and test

---
*This guide was created after troubleshooting mobile register loading issues on 2025-01-25*