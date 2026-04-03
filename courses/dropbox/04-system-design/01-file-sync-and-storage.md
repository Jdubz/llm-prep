# 01 – File Sync and Storage

"Design Dropbox" is the classic system design question — and it's especially likely in a Dropbox interview. This module walks through the full design: file sync, chunking, conflict resolution, and the storage layer.

---

## 1. Requirements Clarification

Always start by clarifying scope. Here's what to ask and assume:

### Functional Requirements
- Users can upload, download, and sync files across devices
- Changes on one device propagate to all others
- File sharing with other users
- File versioning (view and restore previous versions)
- Offline support (work offline, sync when reconnected)

### Non-Functional Requirements
- **Consistency** — a file should never be partially synced or corrupted
- **Availability** — users should be able to access files even if some servers are down
- **Latency** — file operations should feel instantaneous for small files
- **Scale** — 700M+ registered users, exabytes of storage, billions of files
- **Bandwidth efficiency** — minimize data transferred during sync

### Key Numbers

| Metric | Value |
|--------|-------|
| Users | 700M registered, 18M paying |
| Files | Billions |
| Storage | Exabytes |
| Max file size | 50GB (Dropbox limit) |
| Avg file size | ~1MB |
| Peak sync operations | Millions per minute |

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────┐
│                   Client Devices                  │
│   Desktop App / Mobile App / Web App              │
│   [File Watcher] [Sync Engine] [Local Cache]      │
└──────────────┬───────────────────────────────────┘
               │ HTTPS
               ↓
┌──────────────────────────────────────────────────┐
│              API Gateway / Load Balancer           │
└──────┬──────────────┬─────────────────┬──────────┘
       ↓              ↓                 ↓
┌────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Metadata   │ │ Block Server │ │ Notification     │
│ Service    │ │              │ │ Service          │
│ (file tree,│ │ (upload/     │ │ (push sync       │
│ versions,  │ │  download    │ │  events to       │
│ sharing)   │ │  chunks)     │ │  other devices)  │
└─────┬──────┘ └──────┬───────┘ └───────┬──────────┘
      ↓               ↓                 ↓
┌──────────┐   ┌──────────────┐   ┌──────────┐
│ Metadata │   │ Block Storage│   │ Message   │
│ DB       │   │ (Magic      │   │ Queue     │
│ (PostgreSQL)││ Pocket/S3)  │   │ (Kafka)   │
└──────────┘   └──────────────┘   └──────────┘
```

### Component Responsibilities

| Component | Role |
|-----------|------|
| **Sync Engine (client)** | Watches file system, computes diffs, uploads/downloads changed blocks |
| **Metadata Service** | Manages file tree, permissions, versions, sharing — the brain |
| **Block Server** | Handles upload/download of file chunks (blocks) |
| **Block Storage** | Stores actual file content as blocks (Magic Pocket at Dropbox) |
| **Notification Service** | Pushes sync events to other devices when a file changes |
| **Metadata DB** | PostgreSQL — stores file metadata, user accounts, sharing info |
| **Message Queue** | Kafka — decouples sync events from notification delivery |

---

## 3. File Chunking

The most important design decision: **don't upload/download entire files — split them into blocks**.

### Why Chunk?

- **Bandwidth efficiency** — if you edit 1 byte of a 1GB file, only the changed block needs to sync
- **Deduplication** — identical blocks across users are stored once
- **Resume** — interrupted transfers resume from the last block, not the beginning
- **Parallelism** — multiple blocks upload/download concurrently

### Chunking Strategy

**Fixed-size blocks:** Simple, but boundaries shift when content is inserted at the beginning.

**Content-defined chunking (CDC):** Use a rolling hash (Rabin fingerprint) to find chunk boundaries based on content. Inserting a byte only affects one chunk, not all subsequent chunks.

```
File content:    [AAAA|BBBB|CCCC|DDDD]
                  ↓ insert 'X' at position 2
Fixed chunking:  [AAXB|BBCC|CDDD|D___]  ← all chunks shifted!
CDC chunking:    [AAX|ABBB|BCCCC|DDDD]  ← only first chunk changes
```

### Block Size

- Typical: **4MB blocks** (Dropbox uses 4MB)
- Smaller blocks = better dedup, more metadata overhead
- Larger blocks = less metadata, worse bandwidth efficiency
- 4MB is the sweet spot for most file types

### Block Flow

```
Client: File changed
    → Compute block hashes for all blocks
    → Send hash list to Metadata Service
    → Metadata Service returns: "I need blocks [3, 7]" (others already exist)
    → Client uploads only blocks [3, 7] to Block Server
    → Block Server stores in Block Storage
    → Metadata Service updates file version
    → Notification Service pushes update to other devices
```

---

## 4. Sync Protocol

### Change Detection (Client-Side)

1. **File watcher** monitors the local Dropbox folder for changes (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows)
2. Changed file is chunked and hashed
3. Hash list compared against last known state
4. Delta (changed blocks) sent to server

### Sync Flow

```
Device A edits file
    → A: compute new block hashes
    → A: upload changed blocks to Block Server
    → A: update metadata (new version, new block list) in Metadata Service
    → Metadata Service: publish sync event to Message Queue
    → Notification Service: push event to Device B via long-polling / WebSocket
    → B: receive notification "file X updated to version N"
    → B: fetch new metadata from Metadata Service
    → B: compare block lists — identify blocks B doesn't have
    → B: download missing blocks from Block Server
    → B: reassemble file locally
```

### Conflict Resolution

What happens when two devices edit the same file simultaneously?

**Strategy: Last-writer-wins with conflict copies**

```
Device A and Device B both edit file.txt (starting from version 3)
    → A uploads version 4 (A's changes)
    → B tries to upload version 4 (B's changes)
    → Metadata Service: "conflict — file is already version 4"
    → B's version saved as "file (conflicted copy - Device B).txt"
    → Both versions preserved — user resolves manually
```

**More sophisticated:** For collaborative documents, use operational transforms (OT) or CRDTs. But for general file sync, conflict copies are the standard approach.

---

## 5. Storage Layer (Magic Pocket)

### Why Build Your Own Storage?

In 2015, Dropbox was one of AWS S3's largest customers. They built Magic Pocket because:
- **Cost** — storing exabytes in S3 is extremely expensive
- **Control** — optimize for their specific access patterns
- **Performance** — reduce latency for their workload

### Magic Pocket Architecture

```
Block Server receives block
    → Write to Magic Pocket
    → Block stored with:
        - Content-addressed hash (SHA-256)
        - Reed-Solomon erasure coding for durability
        - Replicated across multiple availability zones
    → Durability: 99.999999999% (eleven 9s)
```

**Key properties:**
- **Content-addressed** — block identified by its hash. Same content = same hash = stored once
- **Immutable blocks** — blocks are never modified, only created and garbage collected
- **Erasure coding** — not full replication. Split block into N fragments, any K can reconstruct. More storage-efficient than 3x replication.
- **Written in Rust** — performance-critical, memory-safe

### Deduplication

```
User A uploads file → blocks: [hash1, hash2, hash3]
User B uploads same file → blocks: [hash1, hash2, hash3]
    → Storage: only ONE copy of each block exists
    → Both users' metadata points to the same blocks
```

Cross-user dedup at the block level. At Dropbox's scale, this saves petabytes.

---

## 6. Notification System

How do other devices know a file changed?

### Options

| Approach | Latency | Scalability | Notes |
|----------|---------|-------------|-------|
| **Polling** | Seconds | High | Simple but wasteful bandwidth |
| **Long polling** | ~instant | Medium | Connection held open until event |
| **WebSocket** | ~instant | Medium | Persistent bidirectional connection |
| **Server-Sent Events** | ~instant | High | Unidirectional push, reconnects well |

Dropbox likely uses **long polling** for desktop clients and **WebSocket** for web clients.

### Notification Flow

```
File update committed to Metadata Service
    → Publish event to Kafka: {user_id, file_id, version, device_id}
    → Notification Service consumes event
    → Look up all of user's active devices (excluding the one that made the change)
    → Push notification to each device
    → Device initiates sync
```

---

## 7. Scaling Considerations

### Metadata Scaling

- **Shard by user_id** — each user's metadata is on one shard
- **Read replicas** — most operations are reads (listing files, checking versions)
- **Caching** — hot user sessions cached in Redis/Memcached

### Block Server Scaling

- **Stateless** — any block server can handle any upload/download
- **Horizontal scaling** — add servers behind load balancer
- **CDN** — cache popular blocks at edge locations for faster downloads
- **Geographic distribution** — block servers in multiple regions

### Bandwidth Optimization

- **Delta sync** — only transfer changed blocks (not entire files)
- **Compression** — compress blocks before transfer (LZ4 for speed)
- **Deduplication** — don't transfer blocks the server already has
- **Streaming protocol** — pipeline block uploads, don't wait for each ACK

---

## 8. Interview Template

Use this structure when asked "Design Dropbox":

**Minutes 0-3: Clarify**
- "What type of files? Any size limits?"
- "How many users? How many concurrent?"
- "Is offline support needed?"
- "Do we need versioning?"

**Minutes 3-8: High-level design**
- Draw the architecture diagram (client, metadata service, block server, storage, notifications)
- Explain each component's role in one sentence

**Minutes 8-25: Deep dive**
- **Chunking** — explain CDC, block size, dedup
- **Sync protocol** — change detection, upload flow, download flow
- **Conflict resolution** — last-writer-wins + conflict copies

**Minutes 25-35: Scaling & trade-offs**
- How metadata scales (sharding by user)
- How storage scales (Magic Pocket / erasure coding)
- Bandwidth optimizations (delta sync, compression, dedup)

**Minutes 35-40: Operational concerns**
- Failure modes (what if metadata DB is down? what if block storage is unavailable?)
- Monitoring (sync latency, block upload success rate, conflict rate)
- 10x growth plan

---

## 9. Quick-Fire Answers

**"How does Dropbox handle large files?"** — Content-defined chunking into 4MB blocks. Only changed blocks are synced. Parallel upload/download of blocks.

**"How does dedup work?"** — Content-addressed blocks (SHA-256 hash). Same content hash = same block. Stored once, referenced by many.

**"How does conflict resolution work?"** — Optimistic concurrency. Last writer wins for the canonical version. Conflicting version saved as a conflict copy. User resolves.

**"Why erasure coding over replication?"** — Storage efficiency. 3x replication = 3x storage. Reed-Solomon (e.g., 6+3) = 1.5x storage with same durability.

**"How does offline sync work?"** — Client queues changes locally. On reconnect, sync engine sends all queued changes. Server-side conflict detection handles any conflicts.
