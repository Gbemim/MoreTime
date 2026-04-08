/**
 * Zip extension/dist for Chrome Web Store upload (archive root = dist contents).
 * Requires the `zip` CLI (macOS/Linux).
 */

import { execFileSync } from 'node:child_process';
import { existsSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const extensionRoot = join(__dirname, '..');
const distDir = join(extensionRoot, 'dist');
const outZip = join(extensionRoot, 'moretime-extension-store.zip');

if (!existsSync(distDir)) {
  console.error('dist/ is missing. Run: npm run build');
  process.exit(1);
}

try {
  rmSync(outZip);
} catch {
  /* ignore */
}

execFileSync(
  'zip',
  ['-r', outZip, '.', '-x', '*.DS_Store'],
  { cwd: distDir, stdio: 'inherit' },
);

console.log('Wrote', outZip);
