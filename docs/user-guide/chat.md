# Chat Features

Learn how to interact with the AI assistant about vinyl records in Phonox.

## Getting Started with Chat

### Access Chat Panel

The chat panel is on the left side of the main interface and is always visible.

### Start a Conversation

1. Type your message in the text input at the bottom
2. Press Enter or click the Send button
3. AI responds with information

The chat uses **Claude 3.5 Haiku** for efficient, cost-effective responses.

## Chat Capabilities

### General Vinyl Questions

Ask about vinyl records in general:
- "What makes a first pressing valuable?"
- "How do I identify the condition of a record?"
- "What's the difference between stereo and mono pressings?"
- "Tell me about Beatles vinyl releases"
- "What are the most collectible jazz albums?"

### Record-Specific Chat

When you have a record loaded in VinylCard, chat becomes context-aware:
- "Tell me more about this pressing"
- "What's special about this edition?"
- "What are similar albums I should look for?"
- "Who were the musicians on this record?"
- "What's the history of this label?"

The AI automatically knows:
- Current record's artist and title
- Label and catalog information
- Year and genres
- Any barcode or pressing details

### Web-Enhanced Responses

The chat can search the web in real-time for:
- Current market prices and trends
- Recent sales data
- Pressing variants and editions
- Artist background and discography
- Label history

Simply ask questions like:
- "What's the current market value of this record?"
- "Are there other pressings of this album?"
- "What other albums did this artist release in 1973?"

## Chat Best Practices

### Be Specific

Instead of:
```
"Tell me about this"
```

Try:
```
"What makes the UK first pressing different from the US release?"
```

### Ask Follow-up Questions

The chat maintains conversation context:
```
You: "Tell me about Abbey Road"
AI: [Response about Abbey Road]
You: "What other albums did they release that year?"
AI: [Continues conversation about Beatles' 1969 releases]
```

### Technical Questions

Ask about vinyl technology:
- "What does 180g vinyl mean?"
- "How do I clean vinyl records safely?"
- "What's a gatefold sleeve?"
- "What does DMM mastering mean?"

### Market and Value Questions

Get pricing insights:
- "What's a fair price for this condition?"
- "Has this album increased in value?"
- "What affects vinyl record values?"
- "Are picture discs worth collecting?"

## Chat Integration

### From VinylCard

When viewing a record in VinylCard:
- Chat automatically has record context
- Click "Chat about this record" for direct integration
- AI references current record in responses

### During Identification

While records are being analyzed:
- Chat about general topics
- Ask questions about the analysis process
- Get help with image quality

### In Collection View

Navigate to different records:
- Chat context updates automatically
- Ask comparisons between records
- Get collecting advice

## Chat Features

### Message History

- See full conversation history
- Scroll through previous messages
- Context is maintained within session
- Clear chat to start fresh conversation

### Smart Context Switching

When you load a new record:
- Chat updates to new record context
- Can still reference previous conversations
- AI understands record transitions

### Error Handling

If chat encounters issues:
- Error messages are displayed clearly
- Try rephrasing your question
- Check internet connection
- Refresh page if needed

## Example Conversations

### Identifying Records

```
You: "I have a vinyl with a blue label that says 'Capitol'"
AI: "Capitol Records used different label colors across eras. Blue labels 
typically indicate releases from the 1970s. Can you describe the album 
or show me an image?"
```

### Valuation Questions

```
You: "What's this record worth?"
AI: "Let me search current market data for [Album Name] by [Artist]...
Based on recent sales, this pressing in 'Near Mint' condition typically
sells for €45-60 EUR ($50-65 USD). Values vary by condition and 
pressing variant."
```

### Collecting Advice

```
You: "Should I collect original pressings or reissues?"
AI: "It depends on your goals:
- Original pressings often have better value appreciation
- First pressings may have superior mastering
- Modern reissues can offer better sound quality
- Budget matters - reissues are more affordable
What's your collecting budget and focus?"
```

## Chat Limitations

### What Chat Can Do

✅ Answer general vinyl questions
✅ Provide market insights via web search
✅ Discuss specific records in VinylCard
✅ Give collecting advice
✅ Explain technical terms
✅ Share historical information

### What Chat Cannot Do

❌ Directly modify your collection
❌ Add/delete records from register
❌ Edit metadata in VinylCard
❌ Upload images
❌ Access other users' collections
❌ Perform transactions

Use the UI buttons in VinylCard and VinylRegister for those actions.

## Privacy & Data

- Chat conversations are not stored permanently
- No personal information is collected from chat
- Web searches are performed anonymously
- Record metadata shared with AI for context only
- Clear chat history to remove conversation data

## Tips for Better Results

1. **Be descriptive** - Provide details about what you're asking
2. **Use proper terminology** - "first pressing" vs "reissue"
3. **Ask one question at a time** - Better focus and accuracy
4. **Clarify condition** - Specify "Near Mint" vs "VG+"
5. **Mention pressing details** - Country, year, label color

## Troubleshooting

### Chat Not Responding

- Check internet connection
- Verify backend is running (http://localhost:8000/health)
- Look for error messages in chat
- Refresh the page

### Web Search Not Working

- Tavily API key must be configured in `.env`
- Check API quota/limits
- Try again without web search dependency
- See error details in backend logs

### Context Not Working

- Ensure a record is loaded in VinylCard
- Try reloading the record
- Ask explicitly about the specific album
- Provide more context in your question

## Next Steps

- [Upload and identify records](./uploading.md)
- [Manage your collection](./collection.md)
- [API Reference](../api/endpoints.md)
