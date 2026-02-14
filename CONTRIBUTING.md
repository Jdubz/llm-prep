# Contributing

Thanks for your interest in contributing to LLM Prep! This project aims to be a high-quality, community-maintained resource for learning LLM concepts and Python patterns.

## Ways to Contribute

- **Fix errors** — Spotted a factual mistake, outdated info, or typo? Please open a PR.
- **Improve explanations** — Clearer wording, better examples, or additional context are always welcome.
- **Add content** — New interview questions, patterns, or code examples that fill gaps.
- **Translate** — Help make these materials accessible in other languages.

## Guidelines

### Content

- Keep explanations concise and scannable — these are study materials, not textbooks.
- Code examples should demonstrate patterns, not be runnable applications. Use generic interfaces.
- Stay provider-agnostic. Mention provider-specific details as notes, not as the primary approach.
- Python code should use modern patterns: type hints, dataclasses, async/await, Protocol.
- Target Python 3.12+ syntax.

### Process

1. Fork the repository
2. Create a feature branch (`git checkout -b improve-rag-section`)
3. Make your changes
4. Ensure Python files pass type checking: `mypy --strict <file>`
5. Ensure Python files pass linting: `ruff check <file>`
6. Commit with a clear message describing the change
7. Open a Pull Request

### Commit Messages

Use clear, descriptive commit messages:

```
Add hybrid search explanation to RAG architecture
Fix incorrect cosine similarity formula in concepts
Update model pricing table with latest rates
```

### What We're Looking For

- **Accuracy** — Information should be correct and up-to-date
- **Clarity** — Explanations should be understandable to someone studying for an interview
- **Practicality** — Focus on what actually matters in interviews and real-world usage
- **Conciseness** — Respect the reader's time

### What We're Not Looking For

- Vendor-specific tutorials or SDK walkthroughs
- Runnable application boilerplate (this is a study resource, not a starter template)
- Content that duplicates what's already covered

## Reporting Issues

Use GitHub Issues for:

- Factual errors or outdated information
- Missing topics that are commonly asked in LLM interviews
- Suggestions for better explanations or examples
- Broken links or formatting issues

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
