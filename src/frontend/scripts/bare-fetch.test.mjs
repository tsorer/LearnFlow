// The guard from check-api-types.mjs is only worth its runtime if it still
// matches. These cases are the ways it stopped matching before (T-39).
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { findBareFetch } from './bare-fetch.mjs';

const count = (source) => findBareFetch(source).length;

describe('findBareFetch', () => {
  it('flags a request built outside the typed client', () => {
    expect(count('const r = await fetch("/api/query", { method: "POST" });')).toBe(1);
  });

  it('allows globalThis.fetch as the transport and `fetch:` as its option key', () => {
    expect(count('createClient({ fetch: (...a) => globalThis.fetch(...a) });')).toBe(0);
  });

  it('ignores the word fetch in comments — the reason stripping exists', () => {
    expect(count('// never call fetch( directly\n/* fetch( */\nconst a = 1;')).toBe(0);
  });

  it('sees a bare fetch behind a string containing //', () => {
    // Stripping comments before strings cut this line at the `//`, taking the
    // closing quote with it; the quote pairing then shifted and swallowed the
    // call below, leaving the build green with a bare fetch in the client.
    const source = [
      'const HINT = "nutze api.query // nicht den Endpunkt direkt";',
      'const r = await fetch("/api/query", { method: "POST" });',
    ].join('\n');
    expect(count(source)).toBe(1);
  });

  it('sees a bare fetch between two apostrophes in comments', () => {
    // The mirror image: stripping strings before comments reads the `'` of
    // "don't" as the start of a literal that runs to the one in "it's", so
    // everything between them — the call included — is blanked out.
    const source = [
      "// don't build requests by hand",
      'const r = await fetch("/api/query");',
      "// it's the typed client or nothing",
    ].join('\n');
    expect(count(source)).toBe(1);
  });

  it('is not confused by a URL scheme inside a string', () => {
    expect(count('const base = "https://example.test/api";')).toBe(0);
  });

  it('passes on the client it guards', () => {
    expect(count(readFileSync('src/api/client.ts', 'utf8'))).toBe(0);
  });
});
