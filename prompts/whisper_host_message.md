MEDIA_PATH: {{MEDIA_PATH}}
SRT_PATH: {{SRT_PATH}}
DEST_DIR: {{DEST_DIR}}

Unified output layout: Each media's artifacts live in DEST_DIR, e.g. ./output/<basename>/<basename>.srt, .txt, original media.

Steps (order is mandatory):

1. Use the filesystem MCP tool to check existence of SRT_PATH.
2. IF SRT_PATH EXISTS: skip transcribe_media; ensure DEST_DIR exists; COPY (not move) MEDIA_PATH into DEST_DIR, then DELETE the original file (handle name collisions with suffixes).
3. IF SRT_PATH DOES NOT EXIST:
   a. Call transcribe_media with media_file_path=MEDIA_PATH output_dir=DEST_DIR and WAIT for completion
   b. IF transcribe_media FAILS (throws error): STOP immediately, do NOT move the file, report: ERROR: {{BASENAME}} -> Transcription failed: <error_message>
   c. IF transcribe_media SUCCEEDS: ensure DEST_DIR exists; COPY (not move) MEDIA_PATH into DEST_DIR, then DELETE the original file (handle name collisions with suffixes).

Rules:

- CRITICAL: Never move the file before transcription when SRT does not exist.
- CRITICAL: If transcribe_media fails, do NOT proceed with file operations. Stop and report the error.
- CRITICAL: Use COPY + DELETE instead of MOVE/RENAME to handle cross-device operations (Docker volumes).
- Output strictly one line, no transcript text.
- If skipped: SKIPPED: {{BASENAME}} -> COPIED TO: DEST_PATH
- If done: DONE: {{BASENAME}} -> COPIED TO: DEST_PATH
- If error: ERROR: {{BASENAME}} -> Transcription failed: <error_message>
