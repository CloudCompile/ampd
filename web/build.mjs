// PWA build (#84): one esbuild bundle + static assets copied to ../ampd/web-dist.
// esbuild is the ONLY npm dependency — no framework runtime, no lockfile drama.
// CI runs this as a compile check; the Docker build stage runs it for the image
// (node exists only in that stage — the runtime image has no node).
import { build } from "esbuild";
import { cpSync, mkdirSync, writeFileSync } from "fs";

const OUT = "../ampd/web-dist";
mkdirSync(OUT, { recursive: true });

await build({
  entryPoints: ["src/main.js"],
  bundle: true,
  minify: true,
  outfile: `${OUT}/app.js`,
  format: "iife",
  target: ["es2020"],
  logLevel: "info",
});

for (const f of ["index.html", "manifest.webmanifest", "sw.js", "styles.css",
                 "icon.png"]) {
  try { cpSync(f, `${OUT}/${f}`); } catch { /* optional asset */ }
}

// build stamp — the SW bumps its cache name off this
writeFileSync(`${OUT}/build.json`,
  JSON.stringify({ built: new Date().toISOString() }, null, 1));
console.log("PWA built ->", OUT);
