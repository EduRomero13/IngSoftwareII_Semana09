import { useState } from "react";
import { FileDown, FileText, Loader2 } from "lucide-react";
import { downloadReport, errorMessage } from "../api/client";
import { ErrorAlert, PageTitle } from "../components/ui.jsx";

const TYPES = [
  {
    id: "operational",
    title: "Reporte operacional",
    description: "Alertas y triaje, MTTT, tasa de falsos positivos, top orígenes, auditoría reciente.",
    audience: "Analistas / equipo SOC",
  },
  {
    id: "management",
    title: "Reporte de gestión",
    description: "KPIs, incidentes, estado de cumplimiento ISO 27001 / NIST CSF y recomendaciones.",
    audience: "Dirección / gerencia",
  },
];

const FORMATS = [
  { id: "pdf", label: "PDF", ext: "application/pdf" },
  { id: "docx", label: "Word", ext: "docx" },
  { id: "xlsx", label: "Excel", ext: "xlsx" },
];

export default function Reports() {
  const [type, setType] = useState("operational");
  const [format, setFormat] = useState("pdf");
  const [days, setDays] = useState(30);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const generate = async () => {
    const key = `${type}-${format}`;
    setBusy(key);
    setError("");
    try {
      await downloadReport(type, format, days);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <div>
      <PageTitle
        title="Reportes"
        subtitle="Exportables en PDF, Word y Excel · operacionales y de gestión"
      />
      <ErrorAlert message={error} />

      <div className="grid gap-4 md:grid-cols-2">
        {TYPES.map((item) => (
          <button
            key={item.id}
            onClick={() => setType(item.id)}
            className={`rounded-xl border p-5 text-left transition ${
              type === item.id
                ? "border-sky-500 bg-sky-50 ring-1 ring-sky-500"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-sky-600" />
              <h2 className="font-semibold text-slate-900">{item.title}</h2>
            </div>
            <p className="mt-2 text-sm text-slate-600">{item.description}</p>
            <p className="mt-2 text-xs text-slate-400">Destinatario: {item.audience}</p>
          </button>
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-end gap-4">
          <label className="block">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
              Formato
            </span>
            <div className="flex gap-2">
              {FORMATS.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFormat(f.id)}
                  className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                    format === f.id
                      ? "bg-slate-900 text-white"
                      : "border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
              Período (días)
            </span>
            <input
              type="number"
              min={1}
              max={365}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-28 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>

          <button
            onClick={generate}
            disabled={Boolean(busy)}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
          >
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileDown className="h-4 w-4" />
            )}
            {busy ? "Generando..." : "Generar y descargar"}
          </button>
        </div>

        <div className="mt-4 rounded-lg bg-slate-50 p-4 text-xs text-slate-600">
          <p className="font-semibold text-slate-700">Secciones incluidas:</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5">
            {(type === "operational"
              ? [
                  "Indicadores clave (KPIs): alertas, MTTT, tasa de falsos positivos",
                  "Tendencia de alertas de los últimos 7 días",
                  "Top orígenes de alertas",
                  "Detalle de alertas con veredicto del triaje",
                  "Auditoría reciente (usuario, fecha, hora, acción)",
                ]
              : [
                  "Indicadores clave (KPIs) para dirección",
                  "Tendencia de alertas y distribución por severidad",
                  "Incidentes abiertos y cerrados",
                  "Estado de cumplimiento ISO 27001 (A.8.15, A.5.24, A.5.15) y NIST CSF (DE.AE)",
                  "Recomendaciones de gestión",
                ]
            ).map((section) => (
              <li key={section}>{section}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
