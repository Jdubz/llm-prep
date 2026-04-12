"""
Drill 02 — File Chunker
========================
File transfer techniques — classic Dropbox domain.
Build a chunked upload system with deduplication.

Level 1 — Basic Chunking (10 min)
-----------------------------------
  chunk(data: str, chunk_size: int) -> list[str]
      Split data into chunks of chunk_size characters.
      Last chunk may be smaller.

  reassemble(chunks: list[str]) -> str
      Join chunks back into the original data string.

  get_chunk_count(data: str, chunk_size: int) -> int
      Return the number of chunks needed to store data.

Level 2 — Upload Session (10 min)
-----------------------------------
  init_upload(filename: str, total_chunks: int) -> str
      Start an upload session. Return a unique session_id.

  upload_chunk(session_id: str, chunk_index: int, data: str) -> bool
      Upload a chunk at the given index. Return False if
      session_id is invalid or chunk_index is out of range
      [0, total_chunks). Idempotent: re-uploading the same
      chunk index is allowed (overwrites).

  get_progress(session_id: str) -> float
      Return upload progress from 0.0 to 1.0.
      Return -1.0 if session_id is invalid.

Level 3 — Completion & Integrity (10 min)
-------------------------------------------
  complete_upload(session_id: str) -> str | None
      If all chunks are uploaded, reassemble and return the
      full data string. Return None if any chunks are missing
      or session_id is invalid. Cleans up the session after
      successful completion.

  get_missing_chunks(session_id: str) -> list[int]
      Return sorted list of chunk indices not yet uploaded.
      Return [] if session_id is invalid.

  Chunks can be uploaded in any order (not just sequential).

Level 4 — Deduplication (15 min)
---------------------------------
  compute_hash(data: str) -> str
      Return a hash of the data string. Use hashlib.sha256
      hex digest.

  When uploading a chunk, if a chunk with the same hash
  already exists in the global content store, do not store
  a duplicate copy. The chunk still counts as uploaded for
  that session (it references the existing stored data).

  get_storage_saved() -> int
      Return the total number of characters saved by dedup
      (sum of lengths of all skipped duplicate chunks).

Examples
--------
  fc = FileChunker()
  fc.chunk("HelloWorld!", 4)        # ["Hell", "oWor", "ld!"]
  fc.reassemble(["Hell", "oWor", "ld!"])  # "HelloWorld!"
  sid = fc.init_upload("test.txt", 3)
  fc.upload_chunk(sid, 0, "Hell")   # True
  fc.upload_chunk(sid, 2, "ld!")    # True (out of order)
  fc.get_progress(sid)              # ~0.6667
  fc.get_missing_chunks(sid)        # [1]
  fc.upload_chunk(sid, 1, "oWor")   # True
  fc.complete_upload(sid)           # "HelloWorld!"
"""

import hashlib
import math
import uuid

class FileChunker:
    def __init__(self):
        self.uploads = {}
        self.chunk_index = {
            "duplicates": 0,
        }
        pass

    # ── Level 1 ──────────────────────────────────────────────

    def chunk(self, data: str, chunk_size: int) -> list[str]:
        chunks = []
        end = len(data)
        index = 0
        while index < end:
            chunks.append(data[index:index + chunk_size])
            index += chunk_size

        return chunks
    # REVIEW: Works, but the manual index tracking is doing what range() gives
    # you for free: for i in range(0, len(data), chunk_size) with data[i:i+chunk_size].
    # In an interview, reaching for range with a step argument signals Python fluency.

    def reassemble(self, chunks: list[str]) -> str:
        return "".join(chunks)
    # REVIEW: Clean.

    def get_chunk_count(self, data: str, chunk_size: int) -> int:
        return math.ceil(len(data) / chunk_size)
    # REVIEW: Good. math.ceil is readable. The ceiling-division trick
    # -(-len(data) // chunk_size) avoids the float conversion but is less
    # readable — fine either way in an interview.

    # ── Level 2 ──────────────────────────────────────────────

    def init_upload(self, filename: str, total_chunks: int) -> str:
        """Start upload session, return session_id."""
        session_id = str(uuid.uuid4())
        self.uploads[session_id] = {
            "filename": filename,
            "total_chunks": total_chunks,
            "chunks": [None] * total_chunks,
        }
        return session_id
    # REVIEW: Solid. uuid4 is the right choice for unique IDs.

    def upload_chunk(self, session_id: str, chunk_index: int, data: str) -> bool:
        """Upload a chunk. False if invalid session or index out of range."""
        upload = self.uploads.get(session_id)
        if not upload:
            return False
        if chunk_index >= upload["total_chunks"] or chunk_index < 0:
            return False
        
        # dedupe
        hash = self.compute_hash(data)
        existing_chunk = self.chunk_index.get(hash)
        if existing_chunk:
            data = existing_chunk
            self.chunk_index["duplicates"] += len(data)
        else:
            self.chunk_index[hash] = data

        upload["chunks"][chunk_index] = data
        return True
    # REVIEW: Two things an interviewer might probe:
    # 1. `hash` shadows the built-in hash(). Use `h` or `digest` instead.
    # 2. chunk_index stores hashes mixed with the "duplicates" counter in one
    #    dict. A sha256 hex digest can never equal "duplicates", so it works,
    #    but separating content_store and metadata into distinct dicts
    #    (e.g. self.content_store = {} and self.bytes_saved = 0) is cleaner
    #    and shows you think about data modeling.

    def get_progress(self, session_id: str) -> float:
        """Progress 0.0-1.0, or -1.0 if invalid session."""
        upload = self.uploads.get(session_id)
        if not upload:
            return -1.0
        
        complete = len([c for c in upload["chunks"] if c])
        return complete / upload["total_chunks"]
    # REVIEW: `if c` is falsy for both None AND empty string "". If a chunk
    # were ever an empty string, this would miscount. Safer to use
    # `if c is not None`. Same applies to get_missing_chunks below.

    # ── Level 3 ──────────────────────────────────────────────

    def complete_upload(self, session_id: str) -> str | None:
        """Reassemble if complete, else None. Cleans up session."""
        progress = self.get_progress(session_id)
        if progress < 1.0:
            return None
        upload = self.uploads.get(session_id)
        complete = self.reassemble(upload["chunks"])
        del self.uploads[session_id]
        return complete
    # REVIEW: Works, but relies on float comparison (progress < 1.0).
    # With small integer division this is fine, but an interviewer might ask
    # about floating point precision at scale. Comparing the count of
    # non-None chunks to total_chunks as integers avoids float entirely.

    def get_missing_chunks(self, session_id: str) -> list[int]:
        """Sorted list of missing chunk indices. [] if invalid session."""
        upload = self.uploads.get(session_id)
        if not upload:
            return []
        
        missing_chunks = [i for i, c in enumerate(upload["chunks"]) if not c]
        return missing_chunks
    # REVIEW: Same `if not c` vs `c is None` note as get_progress.
    # Otherwise clean — enumerate + list comp is the right idiom here.

    # ── Level 4 ──────────────────────────────────────────────

    def compute_hash(self, data: str) -> str:
        """SHA-256 hex digest of data."""
        hash = hashlib.sha256(data.encode()).hexdigest()
        return hash
    # REVIEW: Correct. Same `hash` shadowing note as upload_chunk.

    def get_storage_saved(self) -> int:
        """Total characters saved by deduplication."""
        return self.chunk_index["duplicates"]
    # REVIEW: Good fix from before — tracking the running total now.

# ─── Self-Checks (do not edit below this line) ──────────────────

_passed = 0
_failed = 0

def _check(label: str, actual: object, expected: object) -> None:
    global _passed, _failed
    if actual == expected:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        print(f"  ✗ {label}")
        print(f"    expected: {expected!r}")
        print(f"         got: {actual!r}")

def _level(name: str, fn) -> None:
    global _failed
    print(name)
    try:
        fn()
    except NotImplementedError as e:
        print(f"  ○ {e}")
    except Exception as e:
        _failed += 1
        print(f"  ✗ {e}")

def _run_self_checks() -> None:

    def level_1():
        fc = FileChunker()
        # basic chunking
        _check("chunk even split", fc.chunk("abcdef", 3), ["abc", "def"])
        _check("chunk uneven split", fc.chunk("HelloWorld!", 4), ["Hell", "oWor", "ld!"])
        _check("chunk size 1", fc.chunk("abc", 1), ["a", "b", "c"])
        _check("chunk empty string", fc.chunk("", 5), [])
        _check("chunk size larger than data", fc.chunk("hi", 10), ["hi"])
        # reassemble
        _check("reassemble chunks", fc.reassemble(["Hell", "oWor", "ld!"]), "HelloWorld!")
        _check("reassemble empty list", fc.reassemble([]), "")
        # chunk count
        _check("chunk count even", fc.get_chunk_count("abcdef", 3), 2)
        _check("chunk count uneven", fc.get_chunk_count("abcdefg", 3), 3)

    def level_2():
        fc = FileChunker()
        sid = fc.init_upload("test.txt", 3)
        _check("init_upload returns string", isinstance(sid, str), True)
        # upload valid chunk
        _check("upload chunk 0", fc.upload_chunk(sid, 0, "aaa"), True)
        _check("progress after 1/3", fc.get_progress(sid), 1.0 / 3.0)
        # upload out of range
        _check("upload chunk -1 invalid", fc.upload_chunk(sid, -1, "x"), False)
        _check("upload chunk 3 invalid", fc.upload_chunk(sid, 3, "x"), False)
        # invalid session
        _check("upload bad session", fc.upload_chunk("fake", 0, "x"), False)
        _check("progress bad session", fc.get_progress("fake"), -1.0)
        # idempotent re-upload
        _check("re-upload chunk 0", fc.upload_chunk(sid, 0, "bbb"), True)
        _check("progress still 1/3 after re-upload", fc.get_progress(sid), 1.0 / 3.0)

    def level_3():
        fc = FileChunker()
        sid = fc.init_upload("doc.txt", 3)
        # missing chunks before any upload
        _check("all chunks missing", fc.get_missing_chunks(sid), [0, 1, 2])
        # upload out of order
        fc.upload_chunk(sid, 2, "ld!")
        fc.upload_chunk(sid, 0, "Hell")
        _check("missing chunk 1", fc.get_missing_chunks(sid), [1])
        # complete with missing chunk
        _check("complete with missing returns None", fc.complete_upload(sid), None)
        # upload final chunk
        fc.upload_chunk(sid, 1, "oWor")
        _check("no missing chunks", fc.get_missing_chunks(sid), [])
        _check("complete returns data", fc.complete_upload(sid), "HelloWorld!")
        # session cleaned up after complete
        _check("missing chunks after cleanup", fc.get_missing_chunks(sid), [])
        _check("complete again returns None", fc.complete_upload(sid), None)
        # invalid session
        _check("missing chunks invalid session", fc.get_missing_chunks("fake"), [])

    def level_4():
        fc = FileChunker()
        # compute_hash deterministic
        h1 = fc.compute_hash("hello")
        h2 = fc.compute_hash("hello")
        h3 = fc.compute_hash("world")
        _check("hash deterministic", h1, h2)
        _check("hash differs for different data", h1 != h3, True)
        _check("hash is hex string", all(c in "0123456789abcdef" for c in h1), True)
        # dedup within same session
        sid1 = fc.init_upload("a.txt", 3)
        fc.upload_chunk(sid1, 0, "AAA")
        fc.upload_chunk(sid1, 1, "AAA")  # duplicate content
        fc.upload_chunk(sid1, 2, "BBB")
        _check("dedup saved within session", fc.get_storage_saved(), 3)
        # dedup across sessions
        sid2 = fc.init_upload("b.txt", 2)
        fc.upload_chunk(sid2, 0, "AAA")  # already stored globally
        fc.upload_chunk(sid2, 1, "CCC")  # new content
        _check("dedup saved across sessions", fc.get_storage_saved(), 6)
        # chunks still count as uploaded despite dedup
        _check("progress with deduped chunks", fc.get_progress(sid2), 1.0)
        _check("complete with deduped chunks", fc.complete_upload(sid2), "AAACCC")

    _level("Level 1 — Basic Chunking", level_1)
    _level("Level 2 — Upload Session", level_2)
    _level("Level 3 — Completion & Integrity", level_3)
    _level("Level 4 — Deduplication", level_4)

def main() -> None:
    print("\nDrill 02 — File Chunker\n")
    _run_self_checks()
    total = _passed + _failed
    print(f"\n{_passed}/{total} passed")
    if _failed == 0 and total > 0:
        print("All tests passed.")

if __name__ == "__main__":
    main()
