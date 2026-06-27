---
name: efficient-coding
description: 'Apply token-saving and quality-preserving practices on every programming task — writing code, fixing bugs, refactoring, explaining code, or answering technical questions. Use when: efficient coding, code quality, clean code, readable code, reduce tokens, quality preserving.'
---

# Efficient Coding

## Core Principle

Every action has a token cost. The goal is to solve the task with the minimum context needed — not minimum effort, minimum *waste*. Lean context produces faster results and better attention on what matters.

## 1. Context — The Biggest Cost Driver

Context bloat (sending more than the model needs) is responsible for more wasted tokens than any other cause. Attack it first.

**Search before reading:**
- Use Grep/Glob to find the exact file and line range before opening anything.
- Prefer reading a narrower range with `read_file` — aim for +10 lines beyond what you need, not +100.
- If you need to understand a module's shape, search for function/class definitions with `grep_search` (regex: `^(def |class |async def |export function|export class)`).
- If you need an overview, read a summary before diving into details.

## 2. Edit Precision — Don't Repeat Large Contexts

When editing, include only the specific lines needed for context:
- Include 3-5 lines before and after the change to anchor the edit.
- Use `replace_string_in_file` with exact string matching.
- Prefer multiple small edits over one large edit.

## 3. Token-Efficient Communication

- Be concise in responses. Answer directly and precisely.
- Skip boilerplate explanations for standard patterns.
- When exploring alternatives, evaluate the top 2-3, not all possibilities.
- Use bullet points over prose when appropriate.

## 4. Quality-Preserving Shortcuts

- Use standard library functions over custom implementations.
- Leverage existing project patterns and conventions.
- Use established libraries rather than reinventing wheels.
- Apply automated refactoring tools (linters, formatters) instead of manual fixes.
