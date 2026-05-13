# phase171 - report page test mock fix

## Scope
- Stabilize ReportPage test to avoid undefined promise chains.
- Remove ReportPage placeholder/fallback copy and avoid blocking on sources.

## Changes
- Mocked getTaskSources() to resolve null in ReportPage test.
- ReportPage now requires report_structured and stops rendering placeholder copy.
- ReportPage loads report without blocking on /tasks/{id}/sources.
- Added explicit error state when report_structured is missing.

## Tests
- npm --prefix frontend test -- --run src/pages/__tests__/ReportPage.test.tsx
  - Result: PASS
  - Warnings observed:
    - baseline-browser-mapping outdated
    - React.jsx invalid type warning at index.tsx:42

## Notes
- The warnings pre-existed; no production behavior changed in this step.
