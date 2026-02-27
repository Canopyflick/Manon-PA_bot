# Manon PA Bot — Todo

## Features

- [ ] **Implement Meta stub**: pipeline for answering meta questions about the bot/app functionality (e.g. "what can you do?", "how do goals work?", "what reminders do I have set?"). Currently classified as `Meta` by the initial classifier but has no handler — falls through silently.
- [ ] **Long-term goals management**: add a way to set, view and edit long-term goals per user. They are already stored in `manon_users.long_term_goals` and injected into every LLM prompt, but there is currently no interface to manage them via chat.
