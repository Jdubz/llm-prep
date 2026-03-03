# Live Coding and Submission Excellence

> Strategies for live coding sessions, thinking out loud, handling being stuck, and the follow-up review discussion after you submit a take-home.

---

## Live Pair Programming

### Collaboration Signals

Live coding is as much about collaboration as it is about code. The interviewer is evaluating what it would be like to work with you.

**Asking questions:**
- "Would you prefer I optimize for readability or performance here?"
- "I am thinking about using X approach because of Y. Does that align with what you are looking for?"
- "I am not sure about this edge case. Can you clarify the expected behavior for [specific scenario]?"

**Thinking aloud:**
- Narrate your thought process continuously
- "I am considering two approaches here..."
- "Let me first handle the happy path, then I will come back for error cases..."
- "I think this is O(n log n) because..."

**Accepting suggestions:**
- When the interviewer hints, take the hint. They are trying to help you succeed.
- "That is a great point, let me adjust my approach..."
- "I had not considered that. Let me refactor this part..."
- Never dismiss a suggestion without consideration, even if you disagree

**Building on interviewer's ideas:**
- "Building on what you said about caching, I think we could also..."
- Treat it as a real pair programming session, not a test

**Recovering from mistakes:**
- Everyone makes mistakes. How you recover matters more than the mistake.
- "I see the issue — I have an off-by-one error here. Let me fix that."
- Do not panic, do not apologize excessively, just fix it and move on
- If you are stuck, say so: "I am stuck on this part. Let me step back and think about the overall approach."

### The Structure for Live Coding

Restate the problem, explain your approach, write the code while narrating, then test and discuss complexity. This maps well to how interviewers evaluate — they want to see how you think, not just what you produce.

---

## Coding Environment Setup

### Before the Interview

You should have all of this ready before interview season, not the night before.

**Editor configuration:**
- Font size large enough for screen sharing (14pt minimum)
- High-contrast theme (dark or light — just make sure it is readable)
- Line numbers enabled
- Disable distracting notifications and plugins
- Know your keyboard shortcuts for: find/replace, move lines, duplicate lines, multi-cursor

**Boilerplate repos:**
- Have template projects ready for your primary languages
- Pre-configured: linter, formatter, test runner, basic project structure
- Tested — make sure they actually run on your current machine
- Keep them private (do not publish interview templates publicly)

**Terminal setup:**
- Clean prompt (no clutter)
- Aliases for common commands (`alias t="npm test"`, `alias r="npm run dev"`)
- Split terminal if possible — one for running, one for commands

### Live Coding Setup Checklist

#### Environment

- [ ] Editor font size 14pt+ (readable when screen sharing)
- [ ] High-contrast theme enabled
- [ ] Line numbers visible
- [ ] Notifications disabled (Slack, email, OS)
- [ ] Clean desktop (no personal tabs/windows visible)
- [ ] Terminal ready with clean prompt
- [ ] Audio/video tested (if remote)
- [ ] Glass of water nearby
- [ ] Quiet environment secured

#### Knowledge

- [ ] Key shortcuts memorized (find, replace, move line, multi-cursor)
- [ ] Standard library functions fresh in mind for your language
- [ ] Common data structure APIs fresh (map, set, heap, queue)
- [ ] Warmed up with one easy problem

#### Materials

- [ ] Job description reviewed
- [ ] Company notes accessible (not visible when sharing screen)
- [ ] Questions prepared for the interviewer

### During the Interview

- Close Slack, email, and all notifications
- Use a clean desktop
- Have a glass of water nearby
- If remote, test your audio/video setup beforehand
- Have the job description and your notes in a separate window (not visible when screen sharing)

---

## Thinking Out Loud

### Why It Matters

Interviewers cannot evaluate what they cannot hear. Your thought process is as important as your solution. A wrong answer with clear reasoning often scores better than a correct answer arrived at silently.

### What to Narrate

**When you read the problem:**
- "Let me restate this to make sure I understand..."
- "I notice the input is sorted, which suggests binary search or two pointers might apply"
- "The constraint says n can be up to 10^6, so I need O(n) or O(n log n)"

**When you are planning:**
- "A brute-force approach would be O(n^2). Let me see if we can do better."
- "I am thinking of using a sliding window here because we need a contiguous subarray"
- "The state I need to track is [X], so a hash map makes sense"

**When you are coding:**
- "I am writing the base case first..."
- "Here I am using a min-heap because I need efficient minimum access..."
- "Let me give this variable a clear name — `leftBoundary` rather than just `l`"

**When you hit an issue:**
- "Wait, this does not handle the case where the array is empty. Let me add that check."
- "I think there might be an off-by-one here. Let me trace through..."
- "Actually, I realize my approach has a problem — let me reconsider."

### Voicing Trade-offs

Every significant decision deserves a sentence of justification:
- "I could use an array here for O(1) access by index, but since the keys are strings, a hash map is more appropriate."
- "Recursive DFS is simpler to write, but I will use iterative to avoid stack overflow on large inputs."
- "I am sorting here which is O(n log n). If we need O(n), we could use a counting sort since values are bounded."

---

## Handling Being Stuck

### Productive Stuck

Being stuck is normal. How you handle it is what matters.

**Step 1: State what you know**
"I know the answer involves comparing elements, and I know the brute force is O(n^2)..."

**Step 2: Try a concrete example**
"Let me trace through with `[3, 1, 4, 1, 5]`..."

**Step 3: Simplify**
"What if the array had only 2 elements? 3 elements?"

**Step 4: Try a different angle**
"What if I think about this from the end instead of the beginning?"

**Step 5: Be transparent**
"I am stuck on this specific part. I have two approaches in mind — let me talk through them and see if either is promising."

### Phrases for Navigating Difficulty

**Starting:**
- "Let me make sure I understand the problem. We need to..."
- "Before I start coding, let me think through my approach..."
- "A few clarifying questions: What is the expected input size? Can there be duplicates?"

**During:**
- "I am going to start with the brute-force approach, then optimize..."
- "I think the right data structure here is X because..."
- "Let me handle the happy path first, then circle back for edge cases..."
- "I notice this is O(n^2). I think we can do better with a hash map..."

**When stuck:**
- "I am stuck on this part. Let me step back and reconsider..."
- "I think the issue is with my [specific area]. Let me trace through..."
- "Can I talk through my current thinking? I see two possible approaches..."

**Finishing:**
- "Let me trace through this with a small example to verify..."
- "The time complexity is O(n log n) due to the sort, and space is O(n)..."
- "With more time, I would add handling for [edge case]..."

### What NOT to Do When Stuck

- Go silent for more than 2 minutes
- Panic visibly (deep breath, continue narrating)
- Abandon your current approach without acknowledging why
- Ask "am I on the right track?" repeatedly — state your approach and let them steer you if needed
- Spend 5 minutes trying to remember a specific API when you could ask or skip it

---

## Live Coding Best Practices

### Before You Type

Do not start typing immediately.

1. **Understand the problem fully** — repeat it back, ask clarifying questions
2. **Write a function signature** — inputs, outputs, then implementation
3. **Discuss your approach** — get buy-in before you commit to a direction
4. **Name things well from the start** — renaming during a live session is awkward

### During Coding

- **Test incrementally** — write a small piece, test it, continue
- **Handle the happy path first** — get something working, then add edge cases
- **If stuck for more than 2 minutes, say something** — "I am considering whether to use X or Y here"
- **Do not delete and rewrite silently** — narrate what you are changing and why
- **Resist over-engineering** — write the simplest thing that works first

### Incremental Testing

Do not write the entire solution before testing:

1. Write the function skeleton with comments
2. Implement the happy path, test it mentally
3. Trace through with a concrete example on paper or in comments
4. Add edge cases one by one
5. Run the actual code if the environment allows

### After Coding

After writing your solution, always do this:
1. **Trace through with a small example** — walk the interviewer through the execution
2. **State the complexity** — time and space, and why
3. **Discuss edge cases** — "This handles empty input because... but if there were duplicates, we would need to..."
4. **Offer improvements** — "With more time, I would optimize the inner loop by..."

---

## The Follow-Up Review Discussion

Many companies follow a take-home with a discussion about your submission. This is where senior candidates can dramatically strengthen (or weaken) their overall impression.

### What They Are Evaluating

- **Can you articulate technical decisions?** — Not just "I chose X" but "I chose X because of Y, and the tradeoff is Z"
- **Do you know the limitations of your code?** — Self-awareness is a senior signal
- **Can you discuss alternatives?** — Shows breadth of knowledge
- **Are you open to feedback?** — How you react to criticism of your code says a lot about working with you
- **Does your verbal explanation match the code?** — They are checking if you actually wrote and understand it

### Common Review Discussion Questions

**"Walk me through your architecture"**
Be ready to explain your decisions in 2-3 minutes. Start with the high-level structure, then dive into key decisions.

**"Why did you choose X over Y?"**
Have specific reasons for your technology and pattern choices. "I chose X because it gave me [specific benefit] for this use case, though Y would be better if [specific condition]."

**"What would you do differently?"**
Reference your README's trade-offs section. Show that you have already thought about this.

**"How would this scale?"**
Think about 10x and 100x the current load. Consider database bottlenecks, memory usage, network calls, and concurrent access.

**"Show me your tests"**
Know your test strategy. Be able to explain what each test covers and why you made coverage decisions the way you did.

**"I noticed [issue]. Can you explain?"**
Do not be defensive. Acknowledge it, explain your reasoning, and discuss how you would fix it. "You are right that this is a potential issue. I made that tradeoff because [reason], but the correct fix would be [solution]."

### Preparing for the Discussion

Before your review session:
1. Re-read your own code — you should be able to explain every line
2. Re-read your README — know your stated trade-offs and assumptions
3. Think about what a reviewer might question — what are the weak points?
4. Prepare 2-3 improvements you would make with more time

---

## Following Up on Take-Home Submissions

### The Submission Email

Keep it brief and professional:

```
Subject: Take-Home Submission - [Your Name] - [Role]

Hi [Name],

I have completed the take-home assignment. The repository is here: [link]

A few highlights:
- [Core feature implemented with brief description]
- [Testing approach]
- [One interesting decision you made]

I documented trade-offs and future improvements in the README.
Please let me know if you have any questions or need anything else.

Best,
[Your Name]
```

### If You Hear Nothing

- **Wait 3-5 business days** before following up
- **Follow up once** — a brief email asking about timeline
- **Do not follow up more than twice** — if they are not responding, move on

---

## Before Live Coding Tips

- **Practice in the actual environment** — if it is CoderPad, practice on CoderPad
- **Warm up** — solve one easy problem to get your brain in gear
- **Prepare your introduction** — "I have been a full-stack engineer for 10+ years, most recently at..."
- **Have questions ready** — for the interviewer, about the role, team, or codebase

## After the Interview

- **Do not second-guess** — what is done is done
- **Write down what went well and what did not** — for next time
- **Follow up** — a brief thank-you email is professional and appropriate
- **Keep your take-home code** — you might want to reference it later or reuse the template
