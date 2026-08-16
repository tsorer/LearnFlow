/**
 * Global test setup — wired via `setupFiles` in vitest.config.ts, so it applies
 * to every test file without any of them having to know about it.
 *
 * Under `environment: "jsdom"` the fetch-related globals come from two
 * different realms: jsdom supplies File, Blob and FormData, while Request,
 * Response and fetch come from Node, because jsdom implements no fetch at all.
 * Across that boundary a request body is unreadable, in one of two ways:
 *
 *   - Node cannot consume the stream of a jsdom File. `request.formData()` and
 *     `request.text()` never settle, which hangs the component under test
 *     mid-request instead of failing it.
 *   - Node's FormData does not recognise a jsdom File as a file and falls back
 *     to stringifying it, so the upload arrives as "[object File]".
 *
 * Either way a test cannot assert what the application actually sent, which is
 * the one thing an API test exists for. Letting the three jsdom overrides fall
 * back to Node's own classes puts everything in one realm and makes multipart
 * and JSON bodies readable.
 *
 * Request, Response and fetch are deliberately NOT touched: they are already
 * Node's, and replacing them — with the undici package, for instance — splits
 * the realm again from the other side. That was measured, not assumed.
 *
 * Known limitations, both wider than the multipart problem this solves:
 *
 *   - jsdom's `new FormData(formElement)` overload is gone, since Node's
 *     FormData takes no arguments. A test that needs it should read the form
 *     fields itself rather than revert this.
 *   - jsdom APIs that validate their arguments against its own internal classes
 *     — FileReader, URL.createObjectURL, DataTransfer — will not accept the
 *     File and Blob instances created here. Nothing in the app uses them today;
 *     the first test that needs one has to construct it from jsdom's class
 *     explicitly, which is still reachable via `window`.
 *
 * The classes are taken from a Response rather than imported from `node:buffer`
 * on purpose. That import would require @types/node, which puts Node's globals
 * into a browser project and quietly changes types the app relies on — most
 * visibly setTimeout/setInterval, which stop returning a number. Parsing one
 * multipart body yields all three classes and costs nothing outside this file.
 */
// Makes this file a module, which top-level await requires. It has nothing to
// export — its whole effect is on the globals below.
export {};

const BOUNDARY = "----learnflowTestProbe";

const probe = await new Response(
  `--${BOUNDARY}\r\n` +
    'Content-Disposition: form-data; name="f"; filename="probe.txt"\r\n' +
    "Content-Type: text/plain\r\n\r\n" +
    `x\r\n--${BOUNDARY}--\r\n`,
  { headers: { "Content-Type": `multipart/form-data; boundary=${BOUNDARY}` } },
).formData();

const probeFile = probe.get("f");
if (!(probeFile instanceof Object) || !("constructor" in probeFile)) {
  throw new Error("Test-Setup: multipart-Probe lieferte keine Datei");
}

globalThis.FormData = probe.constructor as typeof globalThis.FormData;
globalThis.File = probeFile.constructor as typeof globalThis.File;
globalThis.Blob = Object.getPrototypeOf(probeFile.constructor) as typeof globalThis.Blob;
