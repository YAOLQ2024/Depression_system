import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, rmSync, writeFileSync, readFileSync, readdirSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const client = fileURLToPath(new URL("../", import.meta.url));
const output = mkdtempSync(join(tmpdir(), "digital-human-sources-"));
after(() => rmSync(output, { recursive: true, force: true }));
writeFileSync(join(output, "package.json"), '{"type":"module"}');
execFileSync(process.execPath, [
  join(client, "node_modules/typescript/bin/tsc"),
  join(client, "src/lib/digitalHumanSources.ts"),
  "--outDir", output, "--target", "ES2020", "--module", "ES2020", "--strict", "--skipLibCheck",
]);
const { resolveDigitalHumanSource: resolve, getDigitalHumanLayout: layout,
  getClipPlaybackEnd, getDigitalHumanPoster: poster, NEW_DOCTOR_PERSONA_ID: newPersona,
  NEW_DOCTOR_ROOT: newRoot } = await import(pathToFileURL(join(output, "digitalHumanSources.js")));
const publicDir = join(client, "public");
const families = ["consultation-v1", "scale-assessment-v1", "result-v1", "intervention-v1"];
const logicalSources = families.flatMap(family =>
  readdirSync(join(publicDir, "digital-human", family))
    .filter(name => name.endsWith(".webm"))
    .map(name => `/digital-human/${family}/${name}`),
);
const activeSources = logicalSources.filter(source => !source.endsWith("/risk-screening-003.webm"));

test("all original landscape and portrait assets remain the default for both old personas", () => {
  assert.equal(logicalSources.length, 83);
  for (const persona of [undefined, null, "doctor-a-calm-female", "doctor-b-formal-male", "unknown-persona"]) {
    for (const source of logicalSources) {
      const trimmed = `${source}?v=legacy#t=0,6.000`;
      assert.equal(resolve(trimmed, false, persona), trimmed);
      const portrait = resolve(trimmed, true, persona);
      assert.ok(portrait.startsWith("/digital-human/portrait-male-v1/"));
      assert.ok(existsSync(join(publicDir, decodeURI(portrait))));
      assert.equal(layout(source, true, persona), source.endsWith("/risk-screening-003.webm") ? "landscape" : "portrait");
    }
  }
});

test("only the explicit new persona resolves all 82 active clips to the new actor in either direction", () => {
  assert.equal(activeSources.length, 82);
  for (const portrait of [false, true]) {
    for (const source of activeSources) {
      const resolved = resolve(`${source}?v=legacy#t=0,6.000`, portrait, newPersona);
      assert.equal(resolved, `${newRoot}/${source.split("/").at(-1)}`);
      assert.ok(existsSync(join(publicDir, resolved)));
      assert.equal(layout(source, portrait, newPersona), "square");
      assert.equal(getClipPlaybackEnd(resolved, 12.018), 12.018);
    }
  }
});

test("current playlist references and UI-only clips are all covered", () => {
  const resources = join(client, "../../../packages/workflow-resources/digital-human-playlists");
  for (const name of readdirSync(resources).filter(name => name.endsWith(".yaml"))) {
    const yaml = readFileSync(join(resources, name), "utf8");
    for (const match of yaml.matchAll(/\/digital-human\/[^\s"']+\.webm/g)) {
      assert.ok(activeSources.includes(match[0]), match[0]);
      assert.ok(existsSync(join(publicDir, resolve(match[0], false, newPersona))));
    }
  }
  for (const name of ["result-intro-001", "result-severity-none-001", "result-severity-mild-001", "result-severity-moderate-001", "result-severity-severe-001"]) {
    assert.ok(activeSources.includes(`/digital-human/result-v1/${name}.webm`));
  }
  assert.ok(activeSources.includes("/digital-human/scale-assessment-v1/answer-option-reminder-001.webm"));
});

test("invalid nodes and unrelated media keep their URLs; the unused risk clip falls back to original assets", () => {
  for (const source of ["/intervention/video/ocean.mp4", "/digital-human/scale-assessment-v1/sas-021.webm", "/digital-human/consultation-v1/unknown.webm"]) {
    assert.equal(resolve(source, true, newPersona), source);
  }
  const legacy = "/digital-human/consultation-v1/risk-screening-003.webm";
  assert.equal(resolve(legacy, false, newPersona), legacy);
  assert.equal(layout(legacy, true, newPersona), "landscape");
  assert.equal(getClipPlaybackEnd(`${legacy}#t=0,6.000`, 7.111), 6);
  assert.equal(getClipPlaybackEnd(`${legacy}#t=0,6.000`, 5), 5);
});

test("posters follow explicit selection and use the correct original poster when switching back", () => {
  assert.equal(poster(false), "/home-digital-human.png");
  assert.equal(poster(true, "doctor-b-formal-male"), "/digital-human/portrait-male-v1/portrait-male-poster.png");
  assert.equal(poster(false, newPersona), `${newRoot}/poster.png`);
  assert.equal(poster(true, newPersona), `${newRoot}/poster.png`);
  assert.equal(poster(false, null, "/custom.png"), "/custom.png");
});

test("all imported names are normalized and the manifest checksums match the unchanged video bytes", () => {
  const manifest = JSON.parse(readFileSync(join(publicDir, newRoot, "clips.json"), "utf8"));
  assert.equal(manifest.clips.length, 82);
  assert.equal(new Set(manifest.clips.map(clip => clip.filename)).size, 82);
  for (const clip of manifest.clips) {
    assert.ok(!/^\d+\.\s*/.test(clip.filename));
    const bytes = readFileSync(join(publicDir, newRoot, clip.filename));
    assert.equal(bytes.subarray(0, 4).toString("hex"), "1a45dfa3");
    assert.equal(createHash("sha256").update(bytes).digest("hex"), clip.sha256);
    assert.ok(clip.duration_seconds > 0);
  }
});
