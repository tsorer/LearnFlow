// The bare-fetch guard used by check-api-types.mjs (T-39, ADR-010).
//
// Lives in its own module so it can be tested: a guard that quietly stops
// matching is worse than no guard, because the build stays green either way.

// Blanks out comments and string contents so the scan below sees code only.
//
// One pass, not chained .replace calls: these constructs nest, so whichever
// starts first has to consume the others. Removing comments first let a `//`
// inside a string literal cut the line including its closing quote, after which
// the quote pairing shifted and blanked a whole region of the file — a real bare
// fetch in that region went unseen. Removing strings first moves the same hole
// to the apostrophe in a line comment like "don't". The alternation has no order
// to get wrong: the leftmost match wins and the others cannot start inside it.
//
// Strings collapse to `""` instead of vanishing so neighbouring tokens cannot
// fuse into an identifier that was never written.
const COMMENT_OR_STRING = /(["'`])(?:\\.|(?!\1)[^\\])*\1|\/\*[\s\S]*?\*\/|\/\/[^\n]*/g;

export const stripCommentsAndStrings = (source) =>
  source.replace(COMMENT_OR_STRING, (match) => (/^["'`]/.test(match) ? '""' : ''));

// `globalThis.fetch` is the transport openapi-fetch is configured with — the
// one legitimate reference. Anything else building its own request bypasses the
// typed layer and with it every guarantee this guard exists for.
//
// The pattern looks for the identifier rather than a call shape, so whitespace
// before the paren and an aliased reference (`const f = globalThis.fetch`) are
// caught too. Two forms are allowed: `globalThis.fetch` as the transport, and
// `fetch:` as the option key naming it — a key is a name, not a reference.
const BARE_FETCH = /(?<!globalThis\s*\.\s*)\bfetch\b(?!\s*:)/g;

/** Every bare `fetch` reference in `source`, ignoring comments and strings. */
export const findBareFetch = (source) => [
  ...stripCommentsAndStrings(source).matchAll(BARE_FETCH),
];
