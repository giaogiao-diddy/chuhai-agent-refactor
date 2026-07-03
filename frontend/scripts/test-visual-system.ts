import assert from "node:assert";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(__dirname, "..");
const css = readFileSync(join(root, "styles", "app-shell.css"), "utf8");
const shell = readFileSync(join(root, "components", "AppShell.tsx"), "utf8");

assert.ok(css.includes("--color-bg: #F4F9FF"), "visual system uses light blue page background");
assert.ok(css.includes("--color-primary: #1677D2"), "visual system uses blue primary");
assert.ok(css.includes("--color-line: #C8DDF5"), "visual system exposes line color token");
assert.ok(css.includes("linear-gradient(90deg, rgba(126, 182, 239"), "body uses light blue line grid");
assert.ok(css.includes(".shell-brand-mark"), "shell includes brand line mark styles");
assert.ok(css.includes(".shell-line-icon"), "shell uses CSS line icons");
assert.ok(css.includes(".agent-line-panel"), "shared line panel style exists");
assert.ok(css.includes(".score-line-path"), "report path-line signature style exists");

assert.ok(!shell.includes("💬"), "AppShell nav does not use emoji icons");
assert.ok(!shell.includes("📋"), "AppShell nav does not use emoji icons");
assert.ok(!shell.includes("📊"), "AppShell nav does not use emoji icons");
assert.ok(!shell.includes("📚"), "AppShell nav does not use emoji icons");
assert.ok(!shell.includes("⚙️"), "AppShell nav does not use emoji icons");

console.log("Visual system contract passed.");
