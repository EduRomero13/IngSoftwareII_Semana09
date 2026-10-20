import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckSquare, Globe, Radar, ShieldAlert, Zap } from "lucide-react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext.jsx";
import { Badge, ErrorAlert, PageTitle } from "../components/ui.jsx";

const TOOL_LABEL = {
  virustotal: "VirusTotal",
  abuseipdb: "AbuseIPDB",
  geoip: "GeoIP",
};

export default function AlertDetail() {
  const { id } = useParams();
  const { can } = useAuth();
  const [alert, setAlert] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [checked, setChecked] = useState({});

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/alerts/${id}`);
      setAlert(data);
      setError("");
      setChecked({});
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const triage = async () => {
    setBusy(true);
    try {
      await api.post(`/triage/${id}`);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const escalate = async () => {
    setBusy(true);
    try {
      await api.post("/incidents", {
        alert_id: alert.id,
        title: `Incidente: ${alert.title}`,
        severity: alert.triage?.predicted_severity || alert.severity,
        notes: alert.triage?.summary || "",
      });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (status) => {
    try {
      await api.patch(`/alerts/${id}`, { status });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  if (!alert && !error) return <p className="text-sm text-slate-500">Cargando alerta...</p>;
  if (!alert) return <ErrorAlert message={error} />;

  const actions = Array.isArray(alert.triage?.recommended_actions)
    ? alert.triage.recommended_actions
    : [];

  return (
    <div>
      <Link
        to="/alerts"
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="h-4 w-4" /> Volver a alertas
      </Link>
      <PageTitle
        title={`#${alert.id} · ${alert.title}`}
        subtitle={`${alert.source} · regla ${alert.rule_id || "n/a"} · ${new Date(
          alert.created_at + "Z"
        ).toLocaleString("es-PE")}`}
        actions={
          <div className="flex gap-2">
            {alert.status === "pending" && can("triage.execute") && (
              <button
                onClick={triage}
                disabled={busy}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
              >
                <Zap className="h-4 w-4" /> {busy ? "Procesando..." : "Triar ahora"}
              </button>
            )}
            {can("incidents.write") && !alert.incidents?.length && (
              <button
                onClick={escalate}
                disabled={busy}
                className="flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-60"
              >
                <ShieldAlert className="h-4 w-4" /> Escalar a incidente
              </button>
            )}
            {can("alerts.write") && (
              <select
                value={alert.status}
                onChange={(e) => setStatus(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="pending">Pendiente</option>
                <option value="triaged">Triada</option>
                <option value="escalated">Escalada</option>
                <option value="closed">Cerrada</option>
                <option value="discarded">Descartada</option>
              </select>
            )}
          </div>
        }
      />
      <ErrorAlert message={error} />

      <div className="mb-4 flex flex-wrap gap-2">
        <Badge kind="severity" value={alert.severity} />
        <Badge kind="status" value={alert.status} />
        {alert.triage && <Badge kind="verdict" value={alert.triage.llm_verdict} />}
        {alert.triage && (
          <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
            Severidad final: {alert.triage.predicted_severity}
          </span>
        )}
        <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
          Origen: {alert.src_ip} → {alert.dst_ip}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Triaje LLM */}
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <Radar className="h-4 w-4 text-emerald-600" /> Resumen del triaje (LLM)
          </h2>
          {alert.triage ? (
            <>
              <p className="text-sm leading-relaxed text-slate-700">{alert.triage.summary}</p>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                <span>Motor: <b>{alert.triage.engine === "llm" ? `LLM (${alert.triage.model_name})` : "heurístico (fallback)"}</b></span>
                <span>Confianza: <b>{Math.round(alert.triage.confidence * 100)}%</b></span>
                <span>Latencia: <b>{alert.triage.latency_ms} ms</b></span>
                {alert.triage.tokens_used != null && <span>Tokens: <b>{alert.triage.tokens_used}</b></span>}
              </div>

              <h3 className="mb-2 mt-5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <CheckSquare className="h-3.5 w-3.5" /> Acciones recomendadas
              </h3>
              <ul className="space-y-1.5">
                {actions.map((action, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={Boolean(checked[index])}
                      onChange={() => setChecked((prev) => ({ ...prev, [index]: !prev[index] }))}
                    />
                    <span className={checked[index] ? "line-through opacity-50" : ""}>{action}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              Esta alerta aún no ha sido triada.{" "}
              {can("triage.execute") && "Pulsa «Triar ahora» para ejecutar el agente."}
            </p>
          )}
        </section>

        {/* Enriquecimiento */}
        <section className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
            <Globe className="h-4 w-4 text-sky-600" /> Enriquecimiento contextual
          </h2>
          {alert.enrichments?.length ? (
            <div className="space-y-3">
              {alert.enrichments.map((enrich) => (
                <div key={enrich.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wide text-slate-600">
                      {TOOL_LABEL[enrich.tool] || enrich.tool}
                    </span>
                    <span className="font-mono text-xs text-slate-400">{enrich.key}</span>
                  </div>
                  <pre className="overflow-auto whitespace-pre-wrap text-xs text-slate-600">
                    {JSON.stringify(enrich.value, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Sin datos de enriquecimiento (aún no triada).</p>
          )}
        </section>

        {/* Incidentes vinculados */}
        {alert.incidents?.length > 0 && (
          <section className="rounded-xl border border-red-200 bg-red-50 p-5">
            <h2 className="mb-3 text-sm font-semibold text-red-700">Incidentes vinculados</h2>
            <ul className="space-y-2">
              {alert.incidents.map((incident) => (
                <li key={incident.id} className="rounded-lg bg-white p-3 text-sm">
                  <p className="font-medium text-slate-800">
                    #{incident.id} · {incident.title}
                  </p>
                  <div className="mt-1 flex gap-2">
                    <Badge kind="severity" value={incident.severity} />
                    <Badge kind="status" value={incident.status} />
                    {incident.ticket_id && (
                      <span className="text-xs text-slate-500">Ticket: {incident.ticket_id}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Payload crudo */}
        <section className="rounded-xl border border-slate-200 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-300">Payload crudo (JSON)</h2>
          <pre className="max-h-80 overflow-auto text-xs leading-relaxed text-emerald-300">
            {JSON.stringify(alert.raw_payload, null, 2)}
          </pre>
          {alert.description && (
            <p className="mt-3 text-xs text-slate-400">Descripción: {alert.description}</p>
          )}
        </section>
      </div>
    </div>
  );
}
