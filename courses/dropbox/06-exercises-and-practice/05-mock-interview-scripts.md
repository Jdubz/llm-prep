# 05 – Mock Interview Scripts

Complete mock interview scripts for each stage of the Dropbox pipeline. Use these with a partner, or self-administer by reading questions one at a time and answering out loud.

---

## How to Use

**With a partner:**
1. Give them this doc — they play the interviewer
2. They read the stage instructions and questions
3. They probe with the follow-ups
4. After the mock, use the evaluation rubric to debrief

**Solo practice:**
1. Cover the questions below the current one
2. Set the timer for the stage
3. Answer out loud (not just in your head — verbal fluency matters)
4. Compare against the scoring notes

---

## Mock 1: Recruiter Screen (30 minutes)

### Interviewer Script

> "Hi [Name], thanks for taking the time today. I'm [recruiter] from Dropbox's talent team. I'd love to learn more about your background and tell you about the role. Let's get started."

### Questions (in order)

**1. "Tell me about yourself." (2-3 min)**

Scoring notes:
- [ ] Relevant experience highlighted (full-stack, AI/ML, search)
- [ ] Concise (under 90 seconds ideal)
- [ ] Ends with connection to this role
- [ ] Not a resume recitation

**2. "Why Dropbox? Why this role specifically?" (2 min)**

Scoring notes:
- [ ] Mentions Dash by name
- [ ] Shows understanding of what Dash does
- [ ] Connects to personal experience/interest
- [ ] Not generic ("great company")

**3. "Tell me about a technically challenging project you've worked on recently." (3 min)**

Scoring notes:
- [ ] Clear problem statement
- [ ] Describes their specific contribution (not just the team's)
- [ ] Mentions trade-offs or technical decisions
- [ ] Quantified impact

**4. "What experience do you have with AI/ML products?" (2 min)**

Scoring notes:
- [ ] Concrete examples (not just "I'm interested in AI")
- [ ] Understands the integration challenges (latency, fallbacks, streaming)
- [ ] Bonus: mentions RAG, embeddings, or LLMs specifically

**5. "This is a 0→1 environment — how do you handle ambiguity?" (2 min)**

Scoring notes:
- [ ] Gives a specific example
- [ ] Shows comfort with changing requirements
- [ ] Demonstrates bias toward action (not waiting for perfect specs)

**6. "What are your compensation expectations?" (1 min)**

Scoring notes:
- [ ] Ideally lets recruiter share the range first
- [ ] If pressed, gives a reasonable range aligned with market ($180K-$250K+ total comp)
- [ ] Doesn't undersell

**7. "What's your timeline? Are you in other processes?" (1 min)**

Scoring notes:
- [ ] Honest about timeline
- [ ] Creates healthy urgency if applicable ("I have other processes in late stages")
- [ ] Shows genuine interest in Dropbox specifically

**8. "Do you have any questions for me?" (5 min)**

Scoring notes:
- [ ] Asks 2+ thoughtful questions
- [ ] At least one about the team/product
- [ ] Not questions easily answered by the website

Good questions to ask:
- "What does the Dash Experiences team's roadmap look like for the next quarter?"
- "How does the team balance new AI features vs. improving existing search quality?"
- "What's the team size, and how is work distributed?"

---

## Mock 2: CodeSignal OA Simulation (60 minutes)

This simulates the OA format. Use a coding environment. Set a 60-minute timer.

### Instructions

- You have 4 problems
- You **must** use an AI assistant (Claude, ChatGPT, or similar) — this simulates Cosmo
- Target: solve 3 of 4 correctly to pass
- Language: your choice (Python recommended for speed)

### Problem Set A (Use for first simulation)

**Problem 1 (12 min): Two Sum Variant**

Given an array of file sizes and a target storage limit, find two files whose combined size exactly equals the limit. Return their indices.

```python
def find_files_for_storage(sizes: list[int], target: int) -> list[int]:
    # Input: sizes = [4, 7, 1, 3, 5], target = 8
    # Output: [1, 3]  (sizes[1] + sizes[3] = 7 + 1 = 8... wait: 7+3=10, 7+1=8)
    # Actually: Output: [0, 2]... let me recalculate
    # sizes[0]=4, sizes[1]=7, sizes[2]=1, sizes[3]=3, sizes[4]=5
    # 4+1=5, 4+3=7, 4+5=9, 7+1=8 ✓ → [1, 2]
    pass
```

Test: `find_files_for_storage([4, 7, 1, 3, 5], 8)` → `[1, 2]`

**Problem 2 (15 min): Sliding Window Maximum**

Given an array of API response times and a window size k, find the maximum response time in each sliding window of size k.

```python
def max_response_times(times: list[int], k: int) -> list[int]:
    # Input: times = [1, 3, -1, -3, 5, 3, 6, 7], k = 3
    # Output: [3, 3, 5, 5, 6, 7]
    pass
```

**Problem 3 (18 min): Word Break**

Given a search query and a dictionary of known terms, determine if the query can be segmented into dictionary words.

```python
def can_segment_query(query: str, dictionary: list[str]) -> bool:
    # Input: query = "dropboxdash", dictionary = ["dropbox", "dash", "drop", "box"]
    # Output: True ("dropbox" + "dash")
    pass
```

**Problem 4 (15 min): Flatten Nested Folders**

Given a nested folder structure (as nested lists), flatten it into a single list of file paths.

```python
def flatten_folders(structure, path="") -> list[str]:
    # Input: {"root": {"docs": {"file1.txt": None, "file2.txt": None}, "photos": {"img.png": None}}}
    # Output: ["root/docs/file1.txt", "root/docs/file2.txt", "root/photos/img.png"]
    pass
```

### Problem Set B (Use for second simulation)

**Problem 1 (12 min):** Group Anagrams — group file names that are anagrams of each other.

**Problem 2 (15 min):** Meeting Rooms II — given a list of sync intervals, find the minimum number of sync workers needed.

**Problem 3 (18 min):** Course Schedule — given a list of connector dependencies, determine if all connectors can be initialized.

**Problem 4 (15 min):** Serialize/Deserialize a tree structure representing a folder hierarchy.

### OA Self-Evaluation

- [ ] Used the AI assistant throughout (not just at the end)
- [ ] Solved at least 3 of 4 problems correctly
- [ ] Managed time well (didn't spend 30 min on problem 1)
- [ ] Handled edge cases (empty input, single element)
- [ ] Code runs without errors

---

## Mock 3: Onsite Coding Round (1 hour)

### Interviewer Script

> "Welcome! Today we'll work through a coding problem together. I'd love to hear your thought process as you work. Feel free to ask clarifying questions. We'll start with a base problem and may add follow-ups."

### Problem: Design a File Deduplication System

**Part 1 (15 min):**

> "Given a list of file paths, find all groups of files with identical content. You can read file contents."

Follow-up questions to ask the candidate:
- "How do you handle very large files that don't fit in memory?"
- "What's the time complexity?"

**Part 2 (15 min):**

> "Now optimize: we have millions of files. How do you avoid reading every file completely?"

Expected answer: Group by size first, then partial hash (first 4KB), then full hash only for collisions.

Follow-up: "What hash function and why?"

**Part 3 (15 min):**

> "Make it work across a distributed file system. Files are on different machines."

Expected answer: Map-reduce approach. Each machine computes local hashes. Central coordinator merges results.

Follow-up: "How do you handle a machine going down mid-computation?"

**Part 4 (remaining time):**

> "Now the user wants to keep only one copy and replace others with symlinks/references. How do you do this safely?"

Expected answer: Atomic operations, verification step, rollback plan.

### Evaluation Rubric

| Signal | Score (1-5) |
|--------|-------------|
| Clarified requirements before coding | |
| Communicated approach before writing code | |
| Code was clean and correct | |
| Handled edge cases without prompting | |
| Analyzed complexity without being asked | |
| Responded well to follow-ups | |
| Asked "are there more parts?" | |
| Maintained composure under probing | |

---

## Mock 4: System Design Round (1 hour)

### Interviewer Script

> "Today I'd like you to design a system. I'll give you a problem and I'd like you to drive the conversation. I'll ask questions along the way."

### Problem: Design Dropbox Dash

> "Design a universal search system that lets users search across all their connected apps — Gmail, Slack, Google Drive, Jira, etc. — from a single search bar. Include AI-powered answers."

### Interviewer Probe Points

Use these to challenge the candidate at appropriate moments:

**After requirements (3 min):**
- "What's your latency target?" (Should say: search < 1s, AI answer < 2s)
- "How do you handle permissions?" (Should recognize this as critical)

**After high-level design (8 min):**
- "Walk me through what happens when a user types a query" (End-to-end flow)
- "What's the most challenging component?" (Should identify connector diversity or permission enforcement)

**During deep dive (25 min):**
- "How do you keep the index fresh when content changes?" (Webhooks + polling + periodic full sync)
- "What happens if the AI service is down?" (Graceful degradation — show search results without AI)
- "How do you measure search quality?" (NDCG, click-through rate, reformulation rate)
- "How do you handle a new connector that doesn't support webhooks?" (Polling with configurable intervals)

**Scaling (35 min):**
- "How does this scale to 10M users?" (Shard by user_id, read replicas, geographic distribution)
- "What's your biggest scaling bottleneck?" (Connector API rate limits, index writes)

### Evaluation Rubric

| Signal | Score (1-5) |
|--------|-------------|
| Drove the design independently | |
| Asked good clarifying questions | |
| Architecture was clear and complete | |
| Went deep on 2+ components | |
| Discussed trade-offs explicitly | |
| Addressed scaling proactively | |
| Identified failure modes | |
| Mentioned monitoring/observability | |
| Design was practical, not theoretical | |

---

## Mock 5: Behavioral Round (1 hour)

### Interviewer Script

> "Hi [Name], I'm [hiring manager] for the Dash Experiences team. I'd love to get to know you better and hear about your experiences. I'll ask some behavioral questions — feel free to give specific examples."

### Questions (mapped to AOWE)

**1. Aim Higher (10 min)**

> "Tell me about a time you pushed for a more ambitious approach than what was originally planned."

Follow-ups:
- "What was the risk of the more ambitious approach?"
- "How did you convince your team?"
- "What was the outcome?"

**2. We, Not I (10 min)**

> "Describe a situation where you worked with someone who had a fundamentally different approach than you. How did you handle it?"

Follow-ups:
- "What did you learn from their perspective?"
- "Did you change your approach at all?"
- "How did the collaboration end?"

**3. Own It (10 min)**

> "Tell me about a time you caused or were involved in a production incident. What happened?"

Follow-ups:
- "What was the root cause?"
- "What did you do in the moment?"
- "What safeguards did you put in place afterwards?"
- "How did you communicate to stakeholders?"

**4. Make Work Human (10 min)**

> "How have you made your team environment better for people around you?"

Follow-ups:
- "Give me a specific example"
- "How did you know it was needed?"
- "What was the impact?"

**5. Technical Leadership (10 min)**

> "Tell me about a time you had to make a technical decision with incomplete information."

Follow-ups:
- "What information did you wish you had?"
- "How did you de-risk the decision?"
- "Would you make the same decision today?"

**6. Growth (5 min)**

> "What's something you've learned in the last year that changed how you work?"

**7. Closing (5 min)**

> "Do you have any questions for me about the team, the product, or the role?"

### STAR Evaluation

For each story the candidate tells:

| Element | Score (1-3) | Notes |
|---------|-------------|-------|
| Situation — clear and concise? | | |
| Task — specific responsibility stated? | | |
| Action — "I" not just "we"? Specific steps? | | |
| Result — quantified? Lessons learned? | | |
| Under 2 minutes? | | |
| Mapped to an AOWE value naturally? | | |

---

## Mock Interview Schedule

Run these mocks in order, ideally spread across 1-2 weeks:

| Day | Mock | Duration | Notes |
|-----|------|----------|-------|
| Day 1 | Mock 1: Recruiter Screen | 30 min | Solo or with partner |
| Day 2 | Mock 2: CodeSignal OA (Set A) | 60 min | Solo with AI assistant |
| Day 3 | Mock 3: Onsite Coding | 60 min | With a technical partner |
| Day 4 | Mock 4: System Design | 60 min | With a technical partner |
| Day 5 | Mock 5: Behavioral | 60 min | With any partner |
| Day 7 | Mock 2: CodeSignal OA (Set B) | 60 min | Solo — second simulation |
| Day 8 | Re-run weakest mock | 60 min | Focus on feedback areas |

### After Each Mock

1. Score yourself (or have your partner score you) using the rubric
2. Write down the 3 weakest areas
3. Study the relevant module for those areas
4. Re-run the mock section in 3-4 days

---

## Quick Warm-Up Routine (15 min before real interview)

Do this the morning of each interview stage:

1. **2 min:** Review the stage format (which round, what they assess)
2. **3 min:** Re-read your top 3 STAR stories
3. **3 min:** Review your project deep dive context (if applicable)
4. **2 min:** Review your "Why Dropbox" answer
5. **3 min:** Review your questions to ask
6. **2 min:** Deep breaths. You're prepared. They want you to succeed.
