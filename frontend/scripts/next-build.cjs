const { spawnSync } = require("child_process");
const path = require("path");

const patchPath = path.join(__dirname, "patch-exfat-readlink.cjs").replace(/\\/g, "/");
const nextBin = require.resolve("next/dist/bin/next");
const existingNodeOptions = process.env.NODE_OPTIONS || "";
const nodeOptions = `${existingNodeOptions} --require "${patchPath}"`.trim();

const result = spawnSync(process.execPath, [nextBin, "build"], {
  stdio: "inherit",
  env: {
    ...process.env,
    NODE_OPTIONS: nodeOptions,
  },
});

process.exit(result.status ?? 1);
