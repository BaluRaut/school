# 🇮🇳 The School — Marathi/English i18n

Every site page ships **Marathi by default** with the English original stored in a `data-en`
attribute on each translated element; the top-right dropdown swaps them (choice saved in
`localStorage['school-lang']`).

- `i18n_tool.py` — extract / apply / dump / merge (needs `beautifulsoup4`)
- `mr.json` — the global dictionary: English fragment → Marathi fragment (~3,400 entries)

**After regenerating any generated site** (ai / mcp / agents / vectordb `gen-site.py`), re-apply:

```bash
python3 i18n_tool.py apply mr.json ../learn-ai-school/docs/*.html   # etc.
```

New English strings show up as untranslated: `python3 i18n_tool.py extract mr.json <files>` then
`dump` / `merge` to add Marathi.
