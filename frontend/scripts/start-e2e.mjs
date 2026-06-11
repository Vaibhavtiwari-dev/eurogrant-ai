import { cpSync, existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { join } from "node:path";

const root = process.cwd();
const standaloneRoot = join(root, ".next", "standalone");

if (!existsSync(join(standaloneRoot, "server.js"))) {
  throw new Error("Missing standalone build. Run `npm run build` before E2E tests.");
}

mkdirSync(join(standaloneRoot, ".next"), { recursive: true });
cpSync(join(root, ".next", "static"), join(standaloneRoot, ".next", "static"), {
  recursive: true,
  force: true,
});
cpSync(join(root, "public"), join(standaloneRoot, "public"), {
  recursive: true,
  force: true,
});

const server = spawn(process.execPath, [join(standaloneRoot, "server.js")], {
  cwd: standaloneRoot,
  env: {
    ...process.env,
    HOSTNAME: process.env.HOSTNAME || "localhost",
    PORT: process.env.PORT || "3000",
  },
  stdio: "inherit",
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.kill(signal));
}

server.on("exit", (code) => {
  process.exit(code ?? 0);
});
