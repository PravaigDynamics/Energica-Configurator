/**
 * Upload all layer PNGs to Vercel Blob Storage (private access).
 *
 * Usage:
 *   BLOB_READ_WRITE_TOKEN=<token> node scripts/upload_layers.mjs
 *
 * Prints BLOB_BASE_URL to set in Vercel environment variables.
 */

import { put } from "@vercel/blob";
import { readFileSync, readdirSync, statSync } from "fs";
import { join, extname } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const LAYERS_DIR = join(__dirname, "..", "backend", "layers");

const token = process.env.BLOB_READ_WRITE_TOKEN;
if (!token) {
  console.error(
    "Error: BLOB_READ_WRITE_TOKEN is not set.\n" +
    "Find it in Vercel Dashboard → Storage → Configurator → .env.local tab."
  );
  process.exit(1);
}

const uploadedUrls = [];

for (const model of readdirSync(LAYERS_DIR).sort()) {
  const modelDir = join(LAYERS_DIR, model);
  if (!statSync(modelDir).isDirectory()) continue;

  const pngs = readdirSync(modelDir)
    .filter((f) => extname(f).toLowerCase() === ".png")
    .sort();

  if (pngs.length === 0) {
    console.log(`  [${model}] no PNG files — skipping`);
    continue;
  }

  console.log(`\n[${model}] uploading ${pngs.length} file(s)...`);

  for (const filename of pngs) {
    const filepath = join(modelDir, filename);
    const pathname = `layers/${model}/${filename}`;
    try {
      const data = readFileSync(filepath);
      const result = await put(pathname, data, {
        access: "private",
        token,
        contentType: "image/png",
        allowOverwrite: true,
      });
      uploadedUrls.push(result.url);
      console.log(`  ✓ ${filename}`);
    } catch (err) {
      console.error(`  ✗ ${filename} — ${err.message}`);
    }
  }
}

if (uploadedUrls.length === 0) {
  console.log("\nNo files uploaded.");
  process.exit(1);
}

// Derive base URL: strip the pathname part to get the store root
// URL format: https://<store>.blob.vercel-storage.com/layers/<model>/<file>
const sample = uploadedUrls[0];
const base = sample.split("/layers/")[0];

console.log(`\n${"=".repeat(60)}`);
console.log(`Upload complete. ${uploadedUrls.length} file(s) uploaded.`);
console.log("\nSet this in Vercel → Project → Settings → Environment Variables:");
console.log(`\n  BLOB_BASE_URL = ${base}\n`);
