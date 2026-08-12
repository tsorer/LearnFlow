// Guards the contract between openapi.yaml and the frontend (T-39, ADR-010).
//
// Only one direction needs checking here: that the committed src/api/schema.d.ts
// still matches what the current spec generates. Without it the generated types
// rot silently as soon as the backend changes a schema.
//
// The other direction — "does the client only call declared endpoints" — used to
// live here as a path-scanning check. It is gone because openapi-fetch types the
// paths: `client.GET("/api/nope")` no longer compiles, so `tsc` enforces it more
// thoroughly than a regex could. The guard below only makes sure the client keeps
// going through that typed layer instead of reaching for bare fetch.
import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { delimiter, resolve } from 'node:path';
import { findBareFetch } from './bare-fetch.mjs';

const SPEC = '../backend/openapi.yaml';
const GENERATED = 'src/api/schema.d.ts';
const CLIENT = 'src/api/client.ts';

const fail = (msg) => {
  console.error(`\n${msg}\n`);
  process.exit(1);
};

// Git may check the generated file out with CRLF; the generator always emits LF.
const normalize = (s) => s.replace(/\r\n/g, '\n').trimEnd();

if (!existsSync(SPEC)) {
  fail(`Spec nicht gefunden: ${SPEC}\nAus src/frontend/ ausfuehren (CI und make qa-fe tun das).`);
}

// The same binary `npm run generate:api` uses, so both produce byte-identical
// output. PATH is extended explicitly: npm adds node_modules/.bin only when the
// script runs via `npm run`, and this file must also work when invoked directly.
const generated = spawnSync('openapi-typescript', [SPEC], {
  encoding: 'utf8',
  shell: true,
  env: {
    ...process.env,
    PATH: `${resolve('node_modules/.bin')}${delimiter}${process.env.PATH}`,
  },
});
if (generated.status !== 0) {
  fail(`openapi-typescript ist fehlgeschlagen:\n${generated.stderr ?? ''}`);
}

if (!existsSync(GENERATED)) {
  fail(`${GENERATED} fehlt.\nErzeugen mit: npm run generate:api`);
}

if (normalize(generated.stdout) !== normalize(readFileSync(GENERATED, 'utf8'))) {
  fail(
    `${GENERATED} passt nicht mehr zu ${SPEC}.\n` +
      'Die Spec hat sich geaendert, die generierten Typen nicht.\n' +
      'Beheben mit: npm run generate:api  (und die Datei mitcommitten)',
  );
}

// The scan itself lives in bare-fetch.mjs, where scripts/bare-fetch.test.mjs
// can hold it to its promise — comments and strings must not be able to hide a
// bare fetch from it.
const bareFetch = findBareFetch(readFileSync(CLIENT, 'utf8'));
if (bareFetch.length > 0) {
  fail(
    `${CLIENT} greift direkt auf fetch zu (${bareFetch.length}x).\n` +
      'Alle Requests laufen ueber den typisierten openapi-fetch-Client — nur so\n' +
      'prueft tsc Pfad, Methode, Body und Antwort gegen die Spec.\n' +
      'Erlaubt ist allein `globalThis.fetch` als Transport in createClient.',
  );
}

const pathCount = [...generated.stdout.matchAll(/"(\/api\/[^"]*)":/g)].length;
console.log(`API-Typen aktuell — ${pathCount} Pfade aus ${SPEC}.`);
