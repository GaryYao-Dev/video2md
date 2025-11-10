MEDIA_PATH: {{MEDIA_PATH}}
SRT_PATH: {{SRT_PATH}}
DEST_DIR: {{DEST_DIR}}

Unified output layout: Each media's artifacts live in DEST_DIR, e.g. ./output/<basename>/<basename>.srt, .txt, original media.

Steps (order is mandatory):

1. Use the filesystem MCP tool to check existence of SRT_PATH.
2. IF SRT_PATH EXISTS: skip transcribe_media; ensure DEST_DIR exists; move MEDIA_PATH into DEST_DIR (handle name collisions with suffixes).
3. IF SRT_PATH DOES NOT EXIST: call transcribe_media with media_file_path=MEDIA_PATH output_dir=DEST_DIR and WAIT for completion; then ensure DEST_DIR exists; move MEDIA_PATH into DEST_DIR (handle name collisions with suffixes).

Rules:

- Never move the file before transcription when SRT does not exist.
- Output strictly one line, no transcript text.
- If skipped: SKIPPED: {{BASENAME}} -> MOVED TO: DEST_PATH
- If done: DONE: {{BASENAME}} -> MOVED TO: DEST_PATH
