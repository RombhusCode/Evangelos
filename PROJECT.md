# Evangelos

> A local-first AI communications assistant.

---

# Vision

Evangelos is a personal communications intelligence system.

It is **not** a WhatsApp client.

It is **not** a chatbot.

It is **not** a notification center.

Its purpose is to convert high-volume conversations into structured knowledge and actionable information.

The user should spend less time reading chats and more time understanding what matters.

Every design decision should support this goal.

---

# Core Principles

## Local First

All user data remains on the local machine.

No messages are uploaded to cloud services.

No external APIs are required for normal operation.

Privacy is a non-negotiable requirement.

---

## Source Agnostic

WhatsApp is only the first supported source.

The architecture must support future collectors such as:

- Gmail
- Discord
- Telegram
- Slack
- Google Classroom
- Signal

Collectors should be replaceable without affecting the rest of the system.

---

## Modular Architecture

Each module owns one responsibility.

Business logic should never be tightly coupled.

Dependencies should flow inward.

Example:

Collector
↓

Database

↓

AI

↓

Presentation

Never the reverse.

---

## Human First

The product should prioritize information over raw messages.

Users open Evangelos to answer questions like:

- What happened?
- What changed?
- What requires my attention?
- What should I do next?

The interface should surface knowledge, not conversations.

---

## Simplicity

Avoid unnecessary abstractions.

Prefer readable code over clever code.

Avoid premature optimization.

If a solution is sufficient for one user, do not engineer for one million users.

---

# System Architecture

```
                Evangelos

           Streamlit Dashboard
                    │
      ┌─────────────┴─────────────┐
      │                           │
SQLite Database              Ollama AI
      ▲                           ▲
      └─────────────┬─────────────┘
                    │
        Message Collection Layer
                    │
          WhatsApp Web (Playwright)
```

---

# Technology Stack

Language

- Python 3.12+

User Interface

- Streamlit

Database

- SQLite
- SQLAlchemy ORM

AI

- Ollama
- Local LLMs

Collection

- Playwright

Version Control

- Git
- GitHub

---

# Directory Structure

```
evangelos/

app.py

collector/

database/

ai/

pages/

utils/

data/

tests/

docs/
```

This structure should remain small and understandable.

Avoid deeply nested packages.

---

# Responsibilities

## collector/

Responsible for collecting information.

Must never contain AI logic.

Must never contain UI logic.

Should expose clean interfaces such as:

sync()

fetch_messages()

---

## database/

Responsible only for persistence.

Contains

- models
- sessions
- CRUD operations

No AI.

No UI.

---

## ai/

Responsible for reasoning.

Examples

- summarization
- semantic search
- embeddings
- retrieval
- question answering

Must never directly access WhatsApp.

Reads only from the database.

---

## pages/

Contains Streamlit pages.

Presentation only.

Should not contain business logic.

---

## utils/

Shared helper functions.

Examples

- configuration
- logging
- formatting
- common utilities

---

# Design Rules

Every module should have one responsibility.

Every public function should have a docstring.

Functions should generally remain under ~50 lines unless complexity requires otherwise.

Avoid global state.

Prefer dependency injection where practical.

Avoid circular imports.

Prefer explicit code over magic.

---

# Database Philosophy

SQLite is the system of record.

The database is the single source of truth.

Collectors insert data.

AI reads data.

UI displays data.

Nothing should bypass this flow.

---

# AI Philosophy

The AI never reads WhatsApp directly.

Instead

WhatsApp

↓

Collector

↓

SQLite

↓

AI

↓

Dashboard

This separation keeps the system modular and testable.

---

# User Experience

The dashboard should answer these questions immediately:

What happened today?

Which chats changed?

What requires attention?

Who needs a reply?

What tasks were created?

The user should rarely need to open raw messages.

---

# Code Quality

Every feature should:

- be independently testable
- fail gracefully
- avoid duplicated logic
- include meaningful comments where necessary

Favor maintainability over cleverness.

---

# Git Workflow

One feature per commit.

Commit messages should describe behavior.

Examples

- Add SQLite models
- Implement WhatsApp collector
- Add Streamlit dashboard
- Implement semantic search

Avoid commits such as

- updates
- fixes
- changes

---

# Future Roadmap

Phase 1

- Project scaffold
- SQLite
- Streamlit
- Playwright collector

Phase 2

- AI summaries
- Search
- Assistant

Phase 3

- Semantic search
- Multi-source collectors
- Background synchronization

---

# Instructions for AI Coding Assistants

Before writing code:

1. Preserve the modular architecture.
2. Do not introduce unnecessary dependencies.
3. Prefer simple implementations.
4. Explain architectural decisions when introducing new modules.
5. Do not over-engineer.
6. Keep functions focused and readable.
7. Assume this project will be maintained for years.

When uncertain, choose the simplest solution that preserves clarity.