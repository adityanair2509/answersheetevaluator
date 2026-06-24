# data/

# Runtime data directory — not tracked by git.
#
# Subdirectories created on first `make dev` or `make dirs`:
#   uploads/      — raw uploaded answer sheet images/PDFs
#   ocr_cache/    — cached Google Vision API responses (JSON)
#   chroma/       — ChromaDB vector store persistence
#
# SQLite DB files also live here:
#   evaluator.db  — main application database
#   test.db       — created during test runs (auto-deleted)
