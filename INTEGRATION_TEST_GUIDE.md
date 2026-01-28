# Value Estimation Integration - Testing Guide

## Quick Test Flow

### Desktop Browser
1. Open http://localhost:5173
2. Upload or select a vinyl record (e.g., "Nirvana - Nevermind")
3. Click **🔍 Web Search** button
4. Wait for "Searching..." to complete
5. View the estimated value with:
   - Price range (€XX - €YY)
   - Market condition (strong/stable/weak)
   - [Optional] Factors that affect price
6. Click **✓ Apply** to update the value
7. Verify the new value appears in the record

### Mobile Browser
Same as desktop - responsive design handles the flow:
1. Upload vinyl record
2. Tap "🔍 Web Search"
3. Review market data
4. Tap "✓ Apply"

## What's Different from Before

### Previous Behavior (Problematic)
```
Initial value: €50
Click web search: €50 × 1.2 (mint condition) = €60
Click web search again: €60 × 1.2 = €72
Click web search again: €72 × 1.2 = €86.40
Result: Value keeps growing! ❌
```

### New Behavior (Fixed)
```
Initial value: €50
Click web search: Web search finds €45-55 range → €48 (stable market)
Click web search again: Web search finds €45-55 range → €48 (same result)
Click web search again: Web search finds €45-55 range → €48 (consistent!)
Result: Value based on actual market data ✅
```

## Technical Details

### Frontend Changes
- **File**: `frontend/src/components/VinylCard.tsx`
- **Function**: `recheckValue()`
- **Calls**: `POST /api/v1/estimate-value/{record_id}`
- **Returns**: 
  ```json
  {
    "estimated_value_eur": 48,
    "price_range_min": 45,
    "price_range_max": 55,
    "market_condition": "stable",
    "factors": ["recent reissue", "good condition", "high demand"],
    "explanation": "Market shows stable pricing...",
    "sources_found": 8
  }
  ```

### Backend Endpoint
- **URL**: `POST /api/v1/estimate-value/{record_id}`
- **Process**:
  1. Fetch record from database
  2. Web search: "{artist} {title} vinyl record price"
  3. Claude Haiku analyzes results
  4. **UPDATE** `vinyl_record.estimated_value_eur` (not add)
  5. Return comprehensive valuation data

## Troubleshooting

### "Error checking market value"
- Check backend is running: `docker-compose ps`
- Verify TAVILY_API_KEY is set: `docker-compose logs backend | grep -i tavily`
- Check backend logs: `docker-compose logs backend`

### Value doesn't update
- Verify "✓ Apply" button is clicked (not just the web search)
- Check browser console for errors (F12)
- Verify record_id is being sent correctly

### Search takes too long
- First search may take 10-30 seconds (web search + LLM analysis)
- Subsequent searches same record are faster
- Check internet connection
- Check TAVILY API quota

### Wrong/Unrealistic Values
- Claude Haiku may misinterpret search results
- Check the factors and explanation to understand reasoning
- Factors shown: e.g., "reissue", "original pressing", "condition"
- Market condition: "strong" (high demand), "stable" (normal), "weak" (low demand)

## Verification Checklist

- [ ] Backend endpoint shows in API docs: http://localhost:8000/docs
- [ ] Search button (🔍) appears in VinylCard
- [ ] Clicking search shows "Searching..." animation
- [ ] Value appears with range and condition
- [ ] "✓ Apply" button functional
- [ ] Record value updates in database
- [ ] Works on mobile view (responsive)
- [ ] No console errors (F12 Developer Tools)

## API Endpoint Reference

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/estimate-value/record-uuid-here
```

**Response** (200 OK):
```json
{
  "estimated_value_eur": 48.5,
  "price_range_min": 42.0,
  "price_range_max": 55.0,
  "market_condition": "stable",
  "factors": ["condition", "label", "demand"],
  "explanation": "Market analysis shows...",
  "sources_found": 12,
  "record_id": "uuid",
  "artist": "Nirvana",
  "title": "Nevermind"
}
```

**Error** (422 Unprocessable Entity):
```json
{
  "detail": "Record not found"
}
```

## Features Enabled

✅ Real web search (not simulated)
✅ LLM analysis of market data
✅ Consistent valuations (not accumulating)
✅ Market insight (price range, condition)
✅ Mobile compatible
✅ Cache-busting for mobile refresh
✅ Detailed logging for debugging

## Performance Notes

- **First search**: 10-30 seconds (web search + LLM)
- **Subsequent searches**: 10-30 seconds (same record, fresh search)
- **Database**: Updated in real-time
- **Network**: Requires internet for Tavily web search

---

**Ready to test!** 🎵
