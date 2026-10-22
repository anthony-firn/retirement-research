// No bundler or duplicate UI: copy the shared public web assets into the native package.
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

export function apiOrigin(value) {
  let url;
  try { url = new URL(value); } catch { throw new Error("Set MONEY_PRINTER_API_URL to your household server's HTTPS origin."); }
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || url.pathname !== "/")
    throw new Error("Use an HTTPS origin without credentials, path, query or fragment.");
  if (["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) throw new Error("A phone's localhost is the phone, not the Python server.");
  return url.origin;
}

export async function build(value, destination) {
  const base = apiOrigin(value), here = path.dirname(fileURLToPath(import.meta.url));
  const source = path.resolve(here, "../printer/app/static"), out = destination || path.join(here, "www");
  await readFile(path.join(source, "research/index.html")); // Fail before deleting output if the library was not built.
  await rm(out, { recursive: true, force: true });
  await mkdir(path.join(out, "static"), { recursive: true });
  for (const name of ["app.js", "app.css", "charts.js", "platform.js", "manifest.webmanifest", "vendor", "icons", "research"])
    await cp(path.join(source, name), path.join(out, "static", name), { recursive: true });
  let index = await readFile(path.join(source, "index.html"), "utf8");
  // Capacitor injects its bridge into the bundled document; no development server URL is used.
  await writeFile(path.join(out, "index.html"), index);
  await writeFile(path.join(out, "static/config.js"), "window.PRINTER_CONFIG = Object.freeze(" + JSON.stringify({ apiBase: base, native: true }) + ");\n");
  console.log("Built shared native assets. Endpoint: " + base + "; access key must be supplied at runtime.");
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { await build(process.env.MONEY_PRINTER_API_URL); }
  catch (e) { console.error(e.message); process.exitCode = 1; }
}
