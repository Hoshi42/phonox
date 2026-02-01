# Chat Features

Learn how to interact with the AI chatbot about your vinyl records.

## Getting Started with Chat

### Access Chat

The chat panel is on the left side of the main interface.

Start a conversation:
1. Type your question in the message box
2. Press Enter or click Send
3. AI responds with information about records

## Chat Capabilities

### Ask About Records

**Identify records:**
- "What Beatles albums do I have?"
- "Show me my Pink Floyd collection"
- "List all records from 1975"

**Get information:**
- "Tell me about this album"
- "What's the history of this artist?"
- "Who are the musicians on this record?"

**Get recommendations:**
- "What should I listen to next?"
- "Recommend albums similar to this"
- "What other artists did this producer work with?"

### Query Your Collection

**Search questions:**
- "How many records do I have?"
- "What's the most valuable record I own?"
- "Which condition rating has the most records?"
- "Show me my records from the 1980s"

**Value questions:**
- "What's my collection worth?"
- "Which albums increased in value?"
- "What are rare editions worth?"
- "How does this pressing compare?"

## Advanced Queries

### Complex Searches

Ask multi-part questions:
- "Of my records from the 70s, which ones are worth over €100?"
- "Show me all prog rock albums in excellent condition"
- "Which David Bowie albums do I have and what are they worth?"

### Web Search Integration

Chat can search the web for:
- Current market prices
- Pressing information
- Artist background
- Upcoming releases
- Music news

Prefix question with "Search: " to use web search:
```
Search: What's the current price of this Pink Floyd pressing?
```

## Conversation Context

The AI remembers:
- Your uploaded records
- Your collection
- Previous questions in session
- Album metadata

### Continue Conversations

Reference previous topics:
- "What else did that artist release?"
- "Are those albums also in my collection?"
- "Tell me more about the variations"

## Tips for Better Results

### Be Specific

Instead of:
```
"Tell me about this"
```

Try:
```
"What's special about the 1971 first pressing of this album?"
```

### Use Album Details

Provide context:
- Album title
- Artist name
- Release year
- Pressing country

### Ask Follow-ups

```
Chat: "The Beatles' Abbey Road was released in 1969"
You: "What pressing variations exist?"
Chat: "Several pressings exist from different countries..."
You: "How do I identify which I have?"
```

## Collection Integration

### Chat About Your Records

The AI has access to:
- All records in your collection
- Metadata (artist, title, year, condition)
- Your notes and ratings
- Estimated values

### Example Conversations

**User:** "What's the value trend of my collection?"
**AI:** *Analyzes collection values over time*

**User:** "Which records should I look for?"
**AI:** *Suggests missing albums from artists you own*

**User:** "Compare my pressing to the original"
**AI:** *Details differences and value implications*

## Troubleshooting

**Chat not responding:**
- Check internet connection
- API keys may be invalid
- Restart if unresponsive

**Wrong information:**
- Clarify your question
- Provide more details
- Ask differently

**Missing records:**
- Ensure record is saved to collection
- Chat sees only records you've added
- Upload and save record first

## Chat Command Examples

```
# Collection questions
"Show me my complete collection"
"How many records do I own?"
"What's the most expensive record I have?"

# Artist/Album questions
"Tell me about The Beatles"
"What albums did David Bowie release?"
"Who produced this album?"

# Valuation questions
"What's my collection worth?"
"Is this a valuable pressing?"
"What's the market price?"

# Search questions
"Search: Current price for Pink Floyd DSOTM first pressing"
"Search: Which The Beatles pressing is most valuable"

# Condition/Rating questions
"What records are in excellent condition?"
"How should I rate this album?"
"Rate my collection by condition"
```

## Privacy & Data

- Chat history is NOT stored permanently
- Your collection data is private
- Messages help improve the AI
- Use responsibly

## Advanced Features

### Set Preferences

Configure chat behavior:
- Response style (concise/detailed)
- Web search (always/ask/never)
- Emoji usage (yes/no)

### Export Conversations

Save chat logs:
```bash
# Currently not implemented
# Feature planned for v2.0
```

### Multi-language Support

Chat supports multiple languages:
- English (default)
- German
- French
- Spanish

Specify in preferences.

## Limitations

The AI:
- ✅ Knows public album information
- ✅ Understands vinyl pressing variations
- ✅ Has web search capability
- ✅ Accesses your collection data
- ❌ Cannot make purchase decisions for you
- ❌ Market prices may not be 100% accurate
- ❌ Cannot browse external websites directly

## Getting Help

For chat issues:
1. Refresh the browser
2. Clear browser cache
3. Check API keys in `.env`
4. Restart backend: `docker-compose restart backend`

## Next Steps

- [Manage your collection](./collection.md)
- [View valuations](./valuation.md)
- [Upload more records](./uploading.md)
