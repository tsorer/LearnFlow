import { useState, useEffect, useCallback } from "react";
import type { AuthUser } from "../types";
import { api, ApiError, type ConfigMap } from "../api/client";
import Layout from "./Layout";
import {
  ANSWER_PARAM_DEFS,
  READ_ONLY_PARAM_DEFS,
  RETRIEVAL_PARAM_DEFS,
  type ConfigKey,
  type ParamDef,
} from "../params";

const GROUP_LABEL_STYLE = {
  fontSize: "var(--text-2xs)",
  fontWeight: "var(--font-bold)",
  color: "var(--text-muted)",
  textTransform: "uppercase",
  letterSpacing: ".06em",
  marginBottom: 10,
} as const;

/** One labelled block of sliders. Declared outside the page component so React
 *  keeps the inputs mounted across re-renders — a component defined inside the
 *  parent is a new type on every render and would drop focus after each
 *  keystroke. */
function ParamGroup({
  title,
  defs,
  params,
  onChange,
}: {
  title: string;
  defs: readonly ParamDef[];
  // `ConfigMap`, nicht `Record<string, string>` (T-46): der Zustand oben ist es
  // schon, und nur so sagt der Typ die Nullability richtig. `getConfig` fängt
  // seinen Fehler ab und lässt `params` als `{}` stehen, und in `ConfigMap`
  // ist jeder Schlüssel optional — `params[p.key]` ist zur Laufzeit also
  // wirklich `undefined`. Unter `Record<string, string>` typisierte der
  // Compiler es als `string`, womit das `?? ""` unten wie toter Defensivcode
  // aussieht: wer es entfernt, rendert jeden Regler mit `value={undefined}`
  // und macht die Inputs uncontrolled.
  params: ConfigMap;
  onChange: (key: ConfigKey, value: string) => void;
}) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={GROUP_LABEL_STYLE}>{title}</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "14px 24px" }}>
        {defs.map(p => {
          const raw = params[p.key] ?? "";
          return (
            <div key={p.key}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", fontWeight: "var(--font-bold)", color: "var(--text-primary)", marginBottom: 4 }}>
                <label htmlFor={`param-${p.key}`}>{p.label}</label>
                <input
                  id={`param-${p.key}`}
                  type="number"
                  value={raw}
                  min={p.min} max={p.max} step={p.step}
                  onChange={e => onChange(p.key, e.target.value)}
                  style={{ width: 64, textAlign: "right", fontSize: "var(--text-xs)", padding: "2px 5px", fontWeight: "var(--font-bold)" }}
                />
              </div>
              {p.type === "float" && (
                <input
                  type="range"
                  aria-label={`${p.label} (Schieberegler)`}
                  min={p.min} max={p.max} step={p.step}
                  value={parseFloat(raw) || 0}
                  onChange={e => onChange(p.key, e.target.value)}
                  style={{ width: "100%", accentColor: "var(--coral)", height: 4 }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface Props {
  user: AuthUser;
  onLogout: () => void;
}

/** `/parameter` — used to be a boolean toggled inside ChatView, rendered as an
 *  overlay squeezed between the transcript and the input row (UX pass
 *  2026-09: it is now a real route with room of its own, like every other
 *  Sidebar destination; RouteGuards restricts it to `admin`). */
export default function ParametersPage({ user, onLogout }: Props) {
  const [params, setParams] = useState<ConfigMap>({});
  const [paramSaved, setParamSaved] = useState(false);
  const [paramError, setParamError] = useState("");

  useEffect(() => {
    api.getConfig(user.token).then(setParams).catch(() => {});
  }, []);

  // `ConfigKey`, nicht `string` (T-46): ein Schlüssel, den die config-Tabelle
  // nicht kennt, ist damit ein tsc-Fehler statt einer 422 beim Speichern.
  const updateParam = useCallback((key: ConfigKey, val: string) => {
    setParams(prev => ({ ...prev, [key]: val }));
    setParamSaved(false);
    setParamError("");
  }, []);

  const saveParams = async () => {
    setParamError("");
    try {
      await api.updateConfig(params, user.token);
      // Confirmed only once the write actually returned. Swallowing the
      // rejection showed the green check even when the config table never
      // received it: the admin would go on believing a fail-closed threshold
      // was stored that wasn't (ADR-008).
      setParamSaved(true);
      setTimeout(() => setParamSaved(false), 2000);
    } catch (err) {
      // The backend names the offending key and the rule it broke — a shape
      // violation from `_validate_shape`, or the message of the deferred band
      // trigger ("confidence_threshold_medium (0.8) darf nicht über
      // confidence_threshold_high (0.75) liegen"), which `errorMessage` in the
      // client lifts out of `detail`. Swallowing it left the admin with a panel
      // of ten fields, an all-or-nothing PUT, and nothing to say which one
      // broke — the failure this panel exists to end.
      //
      // `HTTP <status>` is what `errorMessage` returns when it found no usable
      // `detail`, so it is the one message worth replacing: a bare status code
      // helps an admin less than the sentence below.
      const detail =
        err instanceof ApiError && err.message !== `HTTP ${err.status}` ? err.message : null;
      setParamError(detail ?? "Parameter konnten nicht gespeichert werden.");
    }
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-4) var(--space-6)" }}>
        <div style={{ fontWeight: "var(--font-black)", fontSize: "var(--text-xl)", color: "var(--text-primary)", marginBottom: "var(--space-4)" }}>
          Parameter
        </div>

        <div className="card" style={{ padding: "var(--space-6)", maxWidth: 820 }}>
          <ParamGroup
            title="Retrieval · welche Quellen in den Kontext kommen"
            defs={RETRIEVAL_PARAM_DEFS}
            params={params}
            onChange={updateParam}
          />
          <ParamGroup
            title="Antwort · wann der Antwort getraut wird"
            defs={ANSWER_PARAM_DEFS}
            params={params}
            onChange={updateParam}
          />

          {/* Nur zur Ansicht. Eine Änderung wirkt erst nach vollständiger
              Re-Indexierung des Korpus, deshalb weist PUT sie zurück (T-42). */}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 14, marginTop: 4, marginBottom: 20 }}>
            <div style={GROUP_LABEL_STYLE}>Indexierung · erfordert Re-Indexierung, hier nicht änderbar</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "10px 24px" }}>
              {READ_ONLY_PARAM_DEFS.map(p => (
                <div key={p.key} style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-xs)", fontWeight: "var(--font-bold)", color: "var(--text-muted)" }}>
                  <span>{p.label}</span>
                  <span>{params[p.key] ?? "—"}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="primary" onClick={saveParams}>
              Speichern
            </button>
            {paramSaved && <span style={{ fontSize: "var(--text-xs)", color: "var(--olive-text)", fontWeight: "var(--font-semibold)" }}>✓ Gespeichert</span>}
            {paramError && <span style={{ fontSize: "var(--text-xs)", color: "var(--red)", fontWeight: "var(--font-semibold)" }}>{paramError}</span>}
          </div>
        </div>
      </div>
    </Layout>
  );
}
