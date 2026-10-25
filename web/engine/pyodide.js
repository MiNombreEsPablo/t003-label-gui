// Engine seam, browser adapter: the same calls as the desktop bridge, answered by Pyodide in a worker.
//   init(onProgress)  options() -> object  preview(spec) -> {pixels: Uint8Array(W*H gray), hints: string[]}
//   tspl(spec) -> Uint8Array
//   statusProblems(byte) -> string[]
// `spec` is a plain object (the label's JSON); the worker gets it as text.

export function createEngine(baseUrl) {
  const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
  const pending = new Map();
  let nextId = 1;
  let onProgress = () => {};

  worker.onmessage = ({ data }) => {
    if (data.progress !== undefined) return onProgress(data.progress);
    const call = pending.get(data.id);
    pending.delete(data.id);
    if (data.error !== undefined) call.reject(new Error(data.error));
    else call.resolve(data.result);
  };

  const call = (method, args) =>
    new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, method, args });
    });

  return {
    async init(progress) {
      onProgress = progress || onProgress;
      await call("init", { baseUrl });
    },
    async options() {
      return JSON.parse(await call("options"));
    },
    preview: (spec) => call("preview", { spec: JSON.stringify(spec) }),
    tspl: (spec) => call("tspl", { spec: JSON.stringify(spec) }),
    statusProblems: (status) => call("statusProblems", { status }),
  };
}
