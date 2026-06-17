// Fuehrt `tsc --noEmit` aus — aber nur, wenn es ueberhaupt TypeScript-Dateien
// unter src/ gibt. Auf dem noch leeren Scaffold wuerde tsc sonst mit
// "No inputs were found" (TS18003) abbrechen. Sobald die erste .ts/.tsx-Datei
// existiert, greift der Type-Check automatisch.
import { existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const hasTs =
  existsSync('src') &&
  readdirSync('src', { recursive: true }).some((f) => /\.tsx?$/.test(String(f)));

if (!hasTs) {
  console.log('Keine .ts-Dateien — tsc uebersprungen.');
  process.exit(0);
}

const result = spawnSync('tsc', ['--noEmit'], { stdio: 'inherit', shell: true });
process.exit(result.status ?? 1);
