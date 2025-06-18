# LLM Pipeline Debug Logging

This project now includes comprehensive debug logging for the LLM pipeline to help you understand what data is being passed to the LLM and how it responds.

## What Gets Logged

The debug logger captures:

1. **🚀 Pipeline Start**: Conversation ID and user input
2. **👤 User Profile**: Complete user profile information being sent to LLM
3. **🧠 User Memories**: All stored user memories
4. **🔍 Vector Store Search**: The search query sent to the vector store
5. **📚 Retrieved Context**: Documents retrieved from the vector store
6. **🤖 Complete Prompt**: The full prompt template with all variables filled in
7. **🎯 Raw LLM Response**: The unprocessed response from the LLM
8. **✂️ Cleaned Response**: Response after removing code fences
9. **✅ Parsed JSON**: Successfully parsed JSON structure
10. **📋 Final Values**: Extracted reply, summary, and memory
11. **🏁 Pipeline Completion**: Success confirmation

## Where Logs Are Stored

- **File**: `llm_debug.log` (in the project root directory)
- **Encoding**: UTF-8 (supports emojis and special characters)
- **Format**: `YYYY-MM-DD HH:MM:SS - LEVEL - MESSAGE`

## How to View Logs

### Option 1: Using the Debug Viewer Script

```bash
# View entire log
python view_llm_debug.py

# View last 50 lines (most recent interactions)
python view_llm_debug.py tail

# View last 100 lines
python view_llm_debug.py tail 100

# Clear the log file
python view_llm_debug.py clear
```

### Option 2: Using Standard Tools

```bash
# View entire log (Windows)
type llm_debug.log

# View last 50 lines (Windows PowerShell)
Get-Content llm_debug.log -Tail 50

# View entire log (Linux/Mac)
cat llm_debug.log

# View last 50 lines (Linux/Mac)
tail -50 llm_debug.log

# Follow log in real-time (Linux/Mac)
tail -f llm_debug.log
```

### Option 3: Using a Text Editor

Simply open `llm_debug.log` in your favorite text editor (VS Code, Notepad++, etc.)

## Example Log Entry

```
2025-06-19 14:30:15 - INFO - ================================================================================
2025-06-19 14:30:15 - INFO - 🚀 STARTING LLM PIPELINE for conversation 15
2025-06-19 14:30:15 - INFO - 📝 User input: How can I manage my study schedule better?
2025-06-19 14:30:15 - INFO - ================================================================================
2025-06-19 14:30:15 - INFO - 👤 USER PROFILE EXTRACTED:
Bio: Computer Science student at ABC University
About Me: Interested in AI and machine learning
Gender: Male
Address: Student Housing, Campus

Education:
Bachelor's in Computer Science from ABC University batch of 2024 from (2020-09-01 to Present)
2025-06-19 14:30:15 - INFO - --------------------------------------------------
2025-06-19 14:30:15 - INFO - 🧠 USER MEMORIES EXTRACTED:
User mentioned having difficulty with time management
User has midterm exams coming up next week
2025-06-19 14:30:15 - INFO - --------------------------------------------------
...
```

## Troubleshooting

### Log File Too Large?

If the log file becomes too large, you can:

1. Clear it: `python view_llm_debug.py clear`
2. Archive it: Move `llm_debug.log` to `llm_debug_backup_YYYY-MM-DD.log`
3. The system will create a new log file automatically

### Log File Missing?

The log file is created automatically after the first LLM interaction. If it's missing:

1. Make sure you've had at least one conversation with the chatbot
2. Check file permissions in the project directory
3. Verify the Django project has write access to the directory

### Performance Impact

The debug logging is designed to be lightweight, but if you're concerned about performance:

1. The logging only happens during LLM interactions (not on every request)
2. You can disable it by setting the debug logger level to WARNING or higher
3. The log file is written asynchronously and shouldn't block the main thread

## Customization

You can modify the logging behavior in `LLMintegration/chat_utils.py`:

```python
# Change log level
debug_logger.setLevel(logging.WARNING)  # Only log warnings and errors

# Change log file location
debug_handler = logging.FileHandler('/path/to/custom/llm_debug.log', encoding='utf-8')

# Change log format
debug_formatter = logging.Formatter('%(asctime)s - %(message)s')  # Simpler format
```

## Privacy Note

The debug logs contain:
- User messages and profile information
- LLM responses
- Retrieved context from posts/comments

**Make sure to:**
- Keep log files secure
- Don't commit them to version control (add `llm_debug.log` to `.gitignore`)
- Clear logs periodically if they contain sensitive information
- Follow your organization's data privacy policies
