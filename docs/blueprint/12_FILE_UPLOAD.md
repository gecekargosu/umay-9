# 12 — DOSYA UPLOAD

POST /api/upload -> validation -> storage uploads/YYYY-MM/
Validation: extension + size + dangerous + empty
Dedup: SHA-256 hash
List: GET /api/uploads
Test: VERIFIED (TXT,CSV,JSON upload OK, .exe/oversized/empty rejected)
