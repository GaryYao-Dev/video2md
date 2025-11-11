Transcript path: {{TRANSCRIPT_PATH}}
Filename hint: {{FILENAME_HINT}}
User notes/context (optional): {{USER_NOTES}}

Instructions:

- Use the filesystem MCP tool to read the transcript at the provided path.
- If the file is SRT, ignore timestamps and indices; if it's TXT, read as-is.
- IMPORTANT: Start your search with the Filename hint first (include exact string and plausible variants) and incorporate User notes strongly. Treat the filename as the main topic. If some words appear frequently and sound similar to the filename, normalize them to the filename. Prefer filename and user notes over transcript tokens when in conflict.
- Follow your system instructions to parse, extract candidates, search, and fetch sources.
- Prefer primary sources (official GitHub repo or official site).
