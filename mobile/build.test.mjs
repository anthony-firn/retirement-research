import { test } from "node:test";
import assert from "node:assert/strict";
import { apiOrigin, build } from "./build.mjs";
import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

test("native builds require a remote HTTPS origin without embedded credentials", () => {
  for (const value of [undefined, "http://example.org", "https://user:secret@example.org", "https://localhost", "https://example.org/api", "https://example.org/?key=secret"])
    assert.throws(() => apiOrigin(value));
  assert.equal(apiOrigin("https://retirement.example.org/"), "https://retirement.example.org");
});

test("native package uses the shared UI and only the public library", async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), "retirement-build-"));
  try {
    await build("https://retirement.example.org", path.join(dir, "www"));
    const config = await readFile(path.join(dir, "www/static/config.js"), "utf8");
    assert.match(config, /"native":true/);
    assert.match(config, /https:\/\/retirement.example.org/);
    assert.deepEqual((await readdir(path.join(dir, "www"))).sort(), ["index.html", "static"]);
    const page = await readFile(path.join(dir, "www/static/research/index.html"), "utf8");
    assert.match(page, /reconstructed/);
    assert.equal(await readFile(path.join(dir, "www/static/app.js"), "utf8"),
      await readFile(new URL("../printer/app/static/app.js", import.meta.url), "utf8"));
  } finally { await rm(dir, { recursive: true, force: true }); }
});
