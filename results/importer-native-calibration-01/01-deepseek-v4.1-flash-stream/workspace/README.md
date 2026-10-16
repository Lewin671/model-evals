# Stream Ledger

Repair/complete the implementation while preserving its public API. Use only Python's
standard library. You can change ledger/parser.py, ledger/store.py and ledger/api.py.

## API and behavior

- Ingestor(database_path) opens or creates a persistent database. One active writer only.
- feed(stream_id, delivery_id, text, final=False) appends a Unicode CSV fragment and
  returns the number of accepted record revisions, including tombstones. Each pair of
  stream_id/delivery_id identifies one delivery; exact retries return 0 and change nothing.
- Fragments may split anywhere, including quotes, headers and CRLF. Multiple streams
  may be interleaved. Each stream has its own header, pending fragment and delivery IDs.
- CSV has these named columns in any order: id, revision, category, amount_cents, note, op.
  Quoted newlines, escaped quotes, commas and Unicode are valid. Empty physical lines
  are ignored; an empty import or header-only import is valid.
- Commit complete logical records ending in LF or CRLF. final=True also commits a final
  complete record without a newline. An incomplete quoted record at final=True is invalid.
- revision is a positive integer; id is nonempty; op is upsert or delete. Upserts require
  integer amount_cents and preserve category/note. Negative amounts are valid credits.
  Delete rows may leave category/amount/note empty.
- Highest revision wins globally by record ID, independent of arrival order or stream.
  Equal/older revisions are ignored. Deleted IDs retain their revision so older upserts
  cannot resurrect them. A later, higher revision may restore an ID.
- A feed is atomic: invalid complete rows raise ValueError without changing records,
  pending text, delivery bookkeeping or headers, including the in-memory instance.
  A corrected retry of a failed delivery ID must still work.
- Restarting Ingestor must preserve committed records, tombstones, pending text and replay
  bookkeeping. No feed after a stream's final delivery is required, except replay retries.
- records() returns live records sorted lexicographically by ID, with exactly the fields
  id, revision (int), category, amount_cents (int), note. Deleted records are excluded.
- summary() returns {"total_cents": int, "by_category": {category: int}} from live records.
  Keep zero-valued categories if live records remain; remove categories with no live records.
  Repeated summary calls must reflect successful feeds and ignore failed/ignored ones.
- import_csv(database_path, text) remains supported: import a complete CSV document and
  return its summary. Multiple independent files (each with a header) may use one database;
  importing an identical document again is harmless.

## Evaluation tools
Use the native repo_read, repo_write and repo_test tools to inspect, edit and verify the
repository. These are the only repository tools. Do not use shell, web, subagents or the
ordinary filesystem tools. Your final response can be ordinary Markdown; no JSON answer
envelope is required. Runnable source files are graded, not your explanation.

Model-request budget: 3. Batch source reads, source replacements and tests when useful. Final prose is optional; completed files are the goal.
