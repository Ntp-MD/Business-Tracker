/**
 * Mock route `/` — Phase 1 scaffold only.
 * Must stay network-free and separate from the live route. The real mock UI is
 * ported in Phase 6; until then the legacy `index.html` remains the deployed mock.
 */
export default function MockPage() {
  return (
    <main>
      <h1>Mock (scaffold)</h1>
      <p>Sample-data UI is ported in Phase 6. Legacy mock still runs at the repo root.</p>
    </main>
  );
}
