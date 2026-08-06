# Evidence — Tasks 10–12: Frontend (scaffold, process map view, issues/chat panels)

## Stack
Vite + React 19 + TypeScript, Tailwind CSS v4, React Flow (process map DAG
rendering), Vitest + React Testing Library.

## What was built
- `App.tsx`: loads documents/process-map/issues on mount, three-tab layout
  (Process map / Gaps & ambiguities / Ask a question), explicit loading and error
  states (not a blank screen on failure)
- `ProcessMapView` + `TaskNode`: React Flow canvas rendering the 11-task DAG with
  node-type color coding and labeled edges
- `TaskDetailPanel`: task description + click-to-expand citations (per user's "may
  be citations available on click?" direction) — collapsed by default, raw quote +
  page + section + confidence shown on expand
- `IssuesPanel`: renders the 7 logged gaps/ambiguities with type badges and linked
  task titles
- `ChatPanel`: sends questions to `/api/chat`, renders the answer plus clickable
  source chips, and visibly labels retrieval-only vs. LLM-grounded mode

## Real failures caught and fixed (not injected — these were genuine bugs)
1. **`npx tsc --noEmit`**: clean on first pass.
2. **`npx vitest run`**: first real run threw `ReferenceError: ResizeObserver is not
   defined` from inside `@reactflow/core` — jsdom doesn't implement
   `ResizeObserver`, which React Flow requires at mount. 3 test files failed for
   this reason (App.test.tsx). Fixed with a `ResizeObserverPolyfill` in
   `setupTests.ts`. Re-ran: all 14 tests passed.
3. **`npm run build`** (production build, not just the dev/test path): failed with
   `TS2578: Unused '@ts-expect-error' directive` — the `@ts-expect-error` used for
   the ResizeObserver polyfill was necessary under Vitest's tsconfig but flagged as
   unnecessary under the build's stricter `tsc -b` tsconfig. Fixed by switching to
   an explicit type cast instead of a directive that depends on which config is
   checking. Re-ran build: succeeded (`dist/` produced, 343KB JS / 30KB CSS,
   gzipped 108KB/6.5KB). Re-ran tests: still 14/14 green — confirms the fix didn't
   regress the test path while fixing the build path.

## Component/integration test run
```
✓ src/components/IssuesPanel.test.tsx (3 tests)
✓ src/components/TaskDetailPanel.test.tsx (4 tests)
✓ src/components/ChatPanel.test.tsx (3 tests)
✓ src/App.test.tsx (4 tests)
14 passed (14)
```
Notable per verification.md's "enter through the same door as the user" rule:
`TaskDetailPanel.test.tsx`'s citation test explicitly asserts the raw quote is
**absent** before the click and **present** after — not just present eventually —
so the toggle behavior itself is what's being verified, not just final-state
rendering. `ChatPanel.test.tsx` fires a real click on the Send button (not a direct
state call) and asserts the user's own message renders before the network call
resolves, then the assistant reply after.

## Live end-to-end check against the real backend (not mocks)
Started the real FastAPI server (`uvicorn`, port 8811) with the actual seeded AAMI
data, and the real Vite dev server (port 5173) pointed at it via `.env`:
- `curl http://127.0.0.1:8811/api/documents` → real seeded document, `status: ready`
- `curl .../process-map` → 11 tasks / 14 edges, citations with real page numbers
- `curl -X POST .../chat` with "what excess applies if I was not at fault" → correct
  task retrieved (`Determine at-fault status and applicable excess`) with 8 real
  citations attached
- Diffed the live `/issues` and `/process-map` response JSON keys against the
  frontend's TypeScript interfaces (`Citation`, `Issue`, `ProcessTask`) field by
  field — exact match, confirming the frontend's types aren't just internally
  consistent with its own mocks but actually match the real backend contract
- `npm run build` production bundle builds clean against this same API contract

## Known verification gap (disclosed, not glossed over)
This environment's browser tool refuses to navigate to `localhost`/loopback hosts
("navigation blocked: host is a loopback/internal host"), so the actual rendered
UI in a real browser — pixel layout, React Flow's interactive pan/zoom, visual
click-through on the live citation toggle — was **not** visually verified in this
session, only through jsdom-based component tests plus a field-by-field diff of
live API responses against the TypeScript contracts they render. Per
verification.md's "when full verification isn't possible" guidance: the reachable
boundary (component behavior + live API contract match) was tested and is
green; the unreachable layer (actual browser rendering) is named here rather than
silently assumed to work. Recommend a manual click-through in an actual browser
(`cd frontend && npm run dev`, backend running on 8811) before treating this as
fully verified end to end.
