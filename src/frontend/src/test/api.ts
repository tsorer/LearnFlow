/**
 * The shared API stub for component tests.
 *
 * Tests run against `fetch`, not against a mock of `./api/client`: the request
 * that leaves the app is the contract, and everything between the component and
 * the wire — the openapi-fetch client, the serializers, the 401 middleware — is
 * part of what should be under test. Mocking the api module would skip all of
 * it. (auth.test.tsx is the deliberate exception; it mocks the module because
 * it asserts on component behaviour and lets session.test.tsx cover the client.)
 *
 * Every route is typed against openapi.yaml (ADR-010), the same generated
 * schema.d.ts the client is built from. Path, method, status code and response
 * shape all come from the spec, so a test cannot mock an endpoint that does not
 * exist, answer with a status the spec never declares, or return a body the
 * backend could never send. Without that, a mock is the one place left where
 * frontend and contract can drift apart silently — which is exactly what T-39
 * removed everywhere else.
 *
 * Every request is recorded with its parsed body, so a test can assert what was
 * sent and not merely how often. Reading bodies works because src/test/setup.ts
 * puts the fetch globals into a single realm — see the explanation there.
 */
import { vi } from "vitest";
import type { paths } from "../api/schema";

type HttpMethod = "get" | "post" | "put" | "delete" | "patch";

/** A path the spec declares, including the /api prefix nginx rewrites away. */
export type SpecPath = keyof paths;

/**
 * The methods the spec declares for one path. openapi-typescript emits every
 * other verb as `never`, which is what the `responses` probe filters out.
 */
export type SpecMethod<P extends SpecPath> = {
  [M in HttpMethod & keyof paths[P]]: paths[P][M] extends { responses: unknown } ? M : never;
}[HttpMethod & keyof paths[P]];

// M and S are left unconstrained and narrowed by conditionals instead of by
// `extends` clauses: with a generic P, TypeScript cannot prove that
// SpecMethod<P> is a key of paths[P], and every use site would fail on the
// constraint rather than on the actual mistake.
type Responses<P extends SpecPath, M> = M extends keyof paths[P]
  ? paths[P][M] extends { responses: infer R }
    ? R
    : Record<never, never>
  : Record<never, never>;

/** The status codes the spec declares for one operation. */
export type SpecStatus<P extends SpecPath, M> = keyof Responses<P, M>;

/** The JSON body of one declared response, or undefined for 204 and friends. */
type ResponseBody<P extends SpecPath, M, S> = S extends keyof Responses<P, M>
  ? Responses<P, M>[S] extends { content: { "application/json": infer B } }
    ? B
    : undefined
  : undefined;

/**
 * A response without a JSON body takes no body argument at all, one with a body
 * requires it — rather than an optional argument that silently accepts neither.
 */
type BodyArg<P extends SpecPath, M, S> = ResponseBody<P, M, S> extends undefined
  ? []
  : [body: ResponseBody<P, M, S>];

export interface RecordedRequest {
  /** Uppercase, as it appears on the wire. */
  method: string;
  /** The spec path this request matched, e.g. "/api/answers/{answer_id}/feedback". */
  path: string;
  /** The concrete path as requested, e.g. "/api/answers/a1/feedback". */
  url: string;
  /** The Authorization header, or null when the request carried none. */
  authorization: string | null;
  /** Parsed JSON body; undefined unless the request sent application/json. */
  json: unknown;
  /** Parsed multipart body; null unless the request sent multipart/form-data. */
  form: FormData | null;
}

export interface ApiStub {
  /**
   * Registers the answer for one endpoint. Calling it again for the same
   * method and path replaces the answer, which is how a test moves a document
   * from "processing" to "available" or turns a 501 placeholder into a 200.
   */
  route<P extends SpecPath, M extends SpecMethod<P>, S extends SpecStatus<P, M>>(
    method: M,
    path: P,
    status: S,
    ...body: BodyArg<P, M, S>
  ): void;
  /** Every recorded request, optionally narrowed to one endpoint. */
  requests<P extends SpecPath>(method?: SpecMethod<P>, path?: P): RecordedRequest[];
  /** How many requests reached one endpoint. Accurate synchronously. */
  count<P extends SpecPath>(method: SpecMethod<P>, path: P): number;
  /** The most recent request to one endpoint. */
  last<P extends SpecPath>(method: SpecMethod<P>, path: P): RecordedRequest | undefined;
  /**
   * Holds every answer until `release()`. The window in which a request is
   * still in flight is where double submits live, so tests need to open it
   * deliberately. Requests are recorded on arrival, so `count()` stays usable
   * while responses are held.
   */
  hold(): void;
  release(): void;
}

/**
 * Replaces global fetch for the current test. Pair with `vi.unstubAllGlobals()`
 * in afterEach, and call `release()` there too so a held request cannot leave a
 * pending promise behind.
 */
/**
 * Spec paths carry template segments — "/api/answers/{answer_id}/feedback" —
 * while the app requests a concrete one. Tests register the spec path, which is
 * what keeps them typed against openapi.yaml, and this turns it into the
 * pattern that recognises any instantiation of it.
 */
function patternFor(specPath: string): RegExp {
  const escaped = specPath.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`^${escaped.replace(/\\\{[^}]+\\\}/g, "[^/]+")}$`);
}

interface Route {
  method: string;
  path: string;
  pattern: RegExp;
  status: number;
  body?: unknown;
}

export function installApiStub(): ApiStub {
  const routes: Route[] = [];
  const recorded: RecordedRequest[] = [];
  let gate: Promise<void> | null = null;
  let openGate: () => void = () => {};

  async function stub(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    // openapi-fetch hands over a single Request; a bare fetch(url, init) is
    // still possible, so both shapes are normalised before matching.
    const request = input instanceof Request ? input : new Request(String(input), init);
    const url = new URL(request.url, "http://localhost");

    const answer = routes.find(r => r.method === request.method && r.pattern.test(url.pathname));
    if (!answer) throw new Error(`Nicht gemockte Anfrage: ${request.method} ${url.pathname}`);

    // Pushed before the body is parsed, so count() is correct synchronously —
    // a test that clicks three times and asserts immediately must not race the
    // parser. The entry is filled in a moment later.
    const entry: RecordedRequest = {
      method: request.method,
      path: answer.path,
      url: url.pathname,
      authorization: request.headers.get("Authorization"),
      json: undefined,
      form: null,
    };
    recorded.push(entry);

    const type = request.headers.get("Content-Type") ?? "";
    if (type.includes("multipart/form-data")) entry.form = await request.formData();
    else if (type.includes("application/json")) entry.json = await request.json();

    if (gate) await gate;

    return new Response(answer.body === undefined ? null : JSON.stringify(answer.body), {
      status: answer.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  vi.stubGlobal("fetch", vi.fn(stub));

  const matching = (method?: string, path?: string) =>
    recorded.filter(
      r =>
        (method === undefined || r.method === method.toUpperCase()) &&
        (path === undefined || r.path === path),
    );

  return {
    route: (method, path, status, ...body) => {
      const entry: Route = {
        method: String(method).toUpperCase(),
        path: String(path),
        pattern: patternFor(String(path)),
        status: Number(status),
        body: body[0],
      };
      // Replace an existing answer rather than shadowing it: a test that moves
      // a document from "processing" to "available" registers the same route
      // twice, and find() would otherwise keep returning the first one.
      const existing = routes.findIndex(r => r.method === entry.method && r.path === entry.path);
      if (existing === -1) routes.push(entry);
      else routes[existing] = entry;
    },
    requests: (method, path) => matching(method as string | undefined, path as string | undefined),
    count: (method, path) => matching(method as string, path as string).length,
    last: (method, path) => {
      const hits = matching(method as string, path as string);
      return hits[hits.length - 1];
    },
    hold: () => {
      // A second hold() without a release() in between would replace openGate
      // and strand the first promise, so anything already waiting would hang
      // until the test times out. Holding twice simply keeps the first gate.
      if (gate) return;
      gate = new Promise<void>(resolve => {
        openGate = () => {
          gate = null;
          resolve();
        };
      });
    },
    release: () => openGate(),
  };
}

/**
 * The jsdom gaps every test rendering <App /> has to close: the build-time
 * constant Vite injects via define(), the scrollIntoView jsdom does not
 * implement, and a defined starting route.
 */
export function installAppEnvironment(path = "/"): void {
  vi.stubGlobal("__BUILD_TIME__", "2026-08-15T00:00:00.000Z");
  Element.prototype.scrollIntoView = vi.fn();
  window.history.pushState({}, "", path);
}
