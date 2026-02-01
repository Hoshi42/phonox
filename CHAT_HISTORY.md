# Chat History Management

## Overview
Chat history is now persistent per vinyl record with an automatic 10-message pair limit (20 total messages maximum) to prevent memory bloat and maintain optimal performance.

## Features

### Persistence
- **Storage**: Browser localStorage (survives page refreshes)
- **Scope**: Per-record chat history (separate chat for each vinyl record)
- **Automatic Saving**: Messages are automatically saved whenever they change
- **Context Switching**: Switching between records automatically loads the appropriate chat history

### Message Limit
- **Max Messages**: 20 total (10 message pairs = prompt + response)
- **Enforcement**: Applied automatically on every message addition
- **Strategy**: Keeps initial greeting message + last 19 conversation messages
- **Benefit**: Prevents memory leaks and infinite message growth

## Storage Structure

### localStorage Keys
```
phonox_chat_history_{record_id}
```

Example for record ID "rec_12345":
```
phonox_chat_history_rec_12345 = [array of ChatMessage objects]
```

### ChatMessage Format
```typescript
interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  images?: File[]  // Not stored in localStorage
  webEnhanced?: boolean
  sourcesUsed?: number
  searchResults?: Array<{
    title: string
    url: string
    content: string
  }>
}
```

## Implementation Details

### Key Functions

#### `getStoredChatHistory(recordId?: string)`
- Retrieves stored chat history from localStorage for a specific record
- Filters out File objects (cannot be serialized)
- Returns empty array if no history found or on error

#### `saveChatHistory(recordId: string | undefined, messages: ChatMessage[])`
- Saves chat messages to localStorage
- Automatically strips File objects before serialization
- Silently handles errors to prevent disrupting chat functionality

#### `enforceMessageLimit(messages: ChatMessage[], maxMessages: number)`
- Trims message array to maximum size
- Preserves initial greeting message
- Returns only the greeting + last (maxMessages - 1) messages

### Component Behavior

1. **Initial Load**
   - Check localStorage for existing chat history for the record
   - If found, restore it
   - If not found, start with greeting message only

2. **Record Switch**
   - Detect `record?.record_id` change
   - Load appropriate chat history for new record
   - Clear input field

3. **On Every Message**
   - Save to localStorage automatically
   - Enforce 20-message maximum
   - Scroll to bottom

4. **Message Addition**
   - User message → enforce limit → save
   - Assistant message → enforce limit → save
   - System message → enforce limit → save

## Usage

### For Users
- Chat history is automatically maintained per record
- Close browser tab and come back later → history is preserved
- Switch between records → appropriate chat loads
- History never exceeds 20 messages (10 exchanges)

### For Developers

#### To clear chat history for a record:
```javascript
const recordId = "rec_12345"
localStorage.removeItem(`phonox_chat_history_${recordId}`)
```

#### To manually save messages:
```javascript
saveChatHistory(record.record_id, messages)
```

#### To enforce limit on message array:
```javascript
const limitedMessages = enforceMessageLimit(messages, MAX_MESSAGES)
```

## Performance Impact

### Memory Usage
- **Before**: Unbounded growth (could reach 1000+ messages in long sessions)
- **After**: Fixed 20 messages per record
- **Savings**: ~50KB per record (messages + metadata)

### Storage
- **localStorage Limit**: 5-10MB per domain (varies by browser)
- **Per-Record Size**: ~2-5KB (depends on message length)
- **Capacity**: Can store 1000+ records comfortably

### Retrieval Speed
- **Load Time**: <5ms (localStorage is synchronous and fast)
- **No Network Call**: Fully client-side

## Constants

Located in `frontend/src/components/ChatPanel.tsx`:

```typescript
const MAX_MESSAGE_PAIRS = 10        // Keep last 10 pairs
const MAX_MESSAGES = 20             // 10 pairs × 2 = 20 messages
const CHAT_HISTORY_STORAGE_KEY = 'phonox_chat_history'
```

## Browser Compatibility

- ✅ Chrome/Chromium (50+)
- ✅ Firefox (45+)
- ✅ Safari (10.1+)
- ✅ Edge (15+)
- ✅ Mobile browsers (most modern)

## Limitations

1. **File Objects**: Images uploaded are not persisted (files cannot be stored in localStorage)
   - Chat context is preserved, but images must be re-uploaded after refresh
   
2. **No Server Sync**: History is client-side only
   - Not shared between devices
   - Not included in backups
   
3. **localStorage Capacity**: Theoretical 5-10MB per domain
   - At ~3KB per record, this allows 1000+ records
   - Unlikely to be hit in practice

## Future Enhancements

1. **Server-side Storage**
   - Store chat history in database (VinylRecord.chat_history JSONB field)
   - Sync across devices
   - Include in backups
   - Reduce localStorage pressure

2. **Chat Context to Claude**
   - Send last N messages to Claude for better conversational context
   - Currently only send current message

3. **Chat Export**
   - Export chat history as JSON or PDF
   - Share chat transcripts

4. **Search Chat History**
   - Full-text search across past messages
   - Filter by date range

## Testing

### Manual Test Cases

#### Test 1: Persistence
```
1. Open record
2. Send 3-4 messages
3. Close browser/tab
4. Open same record
5. ✓ Chat history should be restored
```

#### Test 2: Record Switching
```
1. Open Record A, send messages
2. Open Record B, send messages
3. Switch back to Record A
4. ✓ Record A's chat should appear
5. Switch to Record B
6. ✓ Record B's chat should appear
```

#### Test 3: Message Limit
```
1. Open record
2. Send 25+ messages rapidly
3. Check browser console: messages.length should be ≤ 20
4. ✓ Greeting message should still be visible
5. ✓ Earlier messages should be trimmed
```

#### Test 4: New Record
```
1. Open new record (not yet chatted with)
2. ✓ Should see greeting message only
3. Send a message
4. ✓ Should be saved to localStorage
```

## Monitoring

### Console Logs
When chat history is loaded/switched:
```
💾 Loaded chat history for record rec_12345: 15 messages
💾 Switched to chat history for record rec_67890: 8 messages
📝 Starting new chat for record rec_11111
```

### Debugging
```javascript
// View all chat history for a record
const history = JSON.parse(localStorage.getItem('phonox_chat_history_rec_12345'))

// View all chat history keys
Object.keys(localStorage).filter(k => k.startsWith('phonox_chat_history_'))
```

## Related Code

- **Component**: [frontend/src/components/ChatPanel.tsx](frontend/src/components/ChatPanel.tsx)
- **API Client**: [frontend/src/api/client.ts](frontend/src/api/client.ts)
- **Backend Chat Route**: [backend/api/routes.py](backend/api/routes.py) (no backend storage currently)
- **Database Schema**: [backend/database.py](backend/database.py) (VinylRecord model)
