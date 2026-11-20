// Runs the harness and one test file in Node the way jsc does: as plain scripts sharing one
// global scope, with jsc's print/load/quit available. Usage: node run_node.js harness.js x.test.js
const fs = require("fs");
const vm = require("vm");

globalThis.print = (...args) => console.log(...args);
globalThis.quit = (code) => process.exit(code);
globalThis.load = (path) => vm.runInThisContext(fs.readFileSync(path, "utf8"), { filename: path });

for (const path of process.argv.slice(2)) load(path);
