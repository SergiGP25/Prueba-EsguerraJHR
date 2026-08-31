"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { BannerError, Etiqueta } from "@/components/ui/Avisos";
import {
  actualizarComprobante,
  contabilizarComprobante,
  crearComprobante,
  revertirComprobante,
} from "@/lib/api";
import { ApiError, mensajeDeError } from "@/lib/errors";
import { aCentavos, aMonto, formatearCentavos } from "@/lib/money";
import type { Comprobante, Cuenta, LineaPayload, Tercero } from "@/lib/types";

interface LineaBorrador {
  clave: string;
  cuentaId: string;
  terceroId: string;
  debito: string;
  credito: string;
  descripcion: string;
}

const lineaVacia = (): LineaBorrador => ({
  clave: crypto.randomUUID(),
  cuentaId: "",
  terceroId: "",
  debito: "",
  credito: "",
  descripcion: "",
});

function lineasIniciales(comprobante?: Comprobante): LineaBorrador[] {
  if (!comprobante) return [lineaVacia(), lineaVacia()];
  return comprobante.lineas.map((linea) => ({
    clave: crypto.randomUUID(),
    cuentaId: String(linea.cuenta_id),
    terceroId: linea.tercero_id ? String(linea.tercero_id) : "",
    debito: linea.debito === "0.00" ? "" : linea.debito,
    credito: linea.credito === "0.00" ? "" : linea.credito,
    descripcion: linea.descripcion ?? "",
  }));
}

const hoy = () => new Date().toISOString().slice(0, 10);

interface Props {
  empresaId: number;
  cuentas: Cuenta[];
  terceros: Tercero[];
  comprobante?: Comprobante;
}

export function ComprobanteForm({ empresaId, cuentas, terceros, comprobante }: Props) {
  const router = useRouter();
  const soloLectura = comprobante ? comprobante.estado !== "borrador" : false;

  const [fecha, setFecha] = useState(comprobante?.fecha ?? hoy());
  const [descripcion, setDescripcion] = useState(comprobante?.descripcion ?? "");
  const [lineas, setLineas] = useState<LineaBorrador[]>(() => lineasIniciales(comprobante));
  const [error, setError] = useState<{ mensaje: string; codigo?: string } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const cuentasActivas = useMemo(() => cuentas.filter((c) => c.activa), [cuentas]);

  // Totales derivados en cada render: no son estado, se calculan de las líneas.
  const { totalDebito, totalCredito, diferencia } = useMemo(() => {
    const debito = lineas.reduce((suma, l) => suma + (aCentavos(l.debito) || 0), 0);
    const credito = lineas.reduce((suma, l) => suma + (aCentavos(l.credito) || 0), 0);
    return { totalDebito: debito, totalCredito: credito, diferencia: debito - credito };
  }, [lineas]);

  const cuadra = diferencia === 0 && totalDebito > 0;

  function actualizarLinea(clave: string, cambios: Partial<LineaBorrador>) {
    setLineas((actuales) =>
      actuales.map((linea) => (linea.clave === clave ? { ...linea, ...cambios } : linea)),
    );
  }

  function reportar(e: unknown) {
    setError({
      mensaje: mensajeDeError(e),
      codigo: e instanceof ApiError ? e.code : undefined,
    });
  }

  function aPayload(): LineaPayload[] {
    return lineas
      .filter((l) => l.cuentaId !== "")
      .map((l) => ({
        cuenta_id: Number(l.cuentaId),
        tercero_id: l.terceroId ? Number(l.terceroId) : null,
        debito: aMonto(aCentavos(l.debito) || 0),
        credito: aMonto(aCentavos(l.credito) || 0),
        descripcion: l.descripcion.trim() || null,
      }));
  }

  async function guardar(contabilizar: boolean) {
    setError(null);
    setOcupado(true);
    try {
      const datos = { fecha, descripcion, lineas: aPayload() };
      const guardado = comprobante
        ? await actualizarComprobante(comprobante.id, datos)
        : await crearComprobante(empresaId, datos);

      if (contabilizar) await contabilizarComprobante(guardado.id);

      router.push(`/comprobantes/${guardado.id}?empresa=${empresaId}`);
      router.refresh();
    } catch (e) {
      reportar(e);
    } finally {
      setOcupado(false);
    }
  }

  async function revertir() {
    if (!comprobante) return;
    setError(null);
    setOcupado(true);
    try {
      const reversion = await revertirComprobante(comprobante.id);
      router.push(`/comprobantes/${reversion.id}?empresa=${empresaId}`);
      router.refresh();
    } catch (e) {
      reportar(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="space-y-6">
      {comprobante && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm">
          <Etiqueta estado={comprobante.estado} />
          <span className="text-slate-600">
            {comprobante.numero ? `Comprobante N.º ${comprobante.numero}` : "Sin numerar"}
          </span>
          {comprobante.reversa_comprobante_id && (
            <span className="text-slate-500">
              Reversa del comprobante interno #{comprobante.reversa_comprobante_id}
            </span>
          )}
        </div>
      )}

      {error && <BannerError mensaje={error.mensaje} codigo={error.codigo} />}

      <div className="grid gap-4 rounded-md border border-slate-200 bg-white p-4 sm:grid-cols-3">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Fecha</span>
          <input
            type="date"
            value={fecha}
            disabled={soloLectura}
            onChange={(e) => setFecha(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1 block font-medium text-slate-700">Descripción</span>
          <input
            type="text"
            value={descripcion}
            disabled={soloLectura}
            placeholder="Compra de insumos"
            onChange={(e) => setDescripcion(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          />
        </label>
      </div>

      <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Cuenta</th>
              <th className="px-3 py-2 font-medium">Tercero</th>
              <th className="px-3 py-2 font-medium">Descripción</th>
              <th className="px-3 py-2 text-right font-medium">Débito</th>
              <th className="px-3 py-2 text-right font-medium">Crédito</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {lineas.map((linea) => (
              <tr key={linea.clave} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-2">
                  <select
                    value={linea.cuentaId}
                    disabled={soloLectura}
                    onChange={(e) => actualizarLinea(linea.clave, { cuentaId: e.target.value })}
                    className="w-56 rounded-md border border-slate-300 px-2 py-1.5 disabled:bg-slate-100"
                  >
                    <option value="">Seleccione…</option>
                    {cuentasActivas.map((cuenta) => (
                      <option key={cuenta.id} value={cuenta.id}>
                        {cuenta.codigo} — {cuenta.nombre}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <select
                    value={linea.terceroId}
                    disabled={soloLectura}
                    onChange={(e) => actualizarLinea(linea.clave, { terceroId: e.target.value })}
                    className="w-48 rounded-md border border-slate-300 px-2 py-1.5 disabled:bg-slate-100"
                  >
                    <option value="">Sin tercero</option>
                    {terceros.map((tercero) => (
                      <option key={tercero.id} value={tercero.id}>
                        {tercero.nombre}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input
                    type="text"
                    value={linea.descripcion}
                    disabled={soloLectura}
                    onChange={(e) => actualizarLinea(linea.clave, { descripcion: e.target.value })}
                    className="w-48 rounded-md border border-slate-300 px-2 py-1.5 disabled:bg-slate-100"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    inputMode="decimal"
                    value={linea.debito}
                    disabled={soloLectura}
                    placeholder="0.00"
                    // Débito y crédito son excluyentes: escribir en uno limpia el otro.
                    onChange={(e) =>
                      actualizarLinea(linea.clave, { debito: e.target.value, credito: "" })
                    }
                    className="w-32 rounded-md border border-slate-300 px-2 py-1.5 text-right disabled:bg-slate-100"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    inputMode="decimal"
                    value={linea.credito}
                    disabled={soloLectura}
                    placeholder="0.00"
                    onChange={(e) =>
                      actualizarLinea(linea.clave, { credito: e.target.value, debito: "" })
                    }
                    className="w-32 rounded-md border border-slate-300 px-2 py-1.5 text-right disabled:bg-slate-100"
                  />
                </td>
                <td className="px-3 py-2 text-right">
                  {!soloLectura && lineas.length > 2 && (
                    <button
                      type="button"
                      onClick={() =>
                        setLineas((actuales) => actuales.filter((l) => l.clave !== linea.clave))
                      }
                      className="text-slate-400 transition-colors hover:text-red-600"
                      aria-label="Eliminar línea"
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!soloLectura && (
        <button
          type="button"
          onClick={() => setLineas((actuales) => [...actuales, lineaVacia()])}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
        >
          + Agregar línea
        </button>
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-slate-200 bg-white px-4 py-3">
        <dl className="flex flex-wrap gap-6 text-sm">
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">Total débito</dt>
            <dd className="font-mono">{formatearCentavos(totalDebito)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">Total crédito</dt>
            <dd className="font-mono">{formatearCentavos(totalCredito)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500">Diferencia</dt>
            <dd
              className={`font-mono font-medium ${
                diferencia === 0 ? "text-emerald-700" : "text-red-700"
              }`}
            >
              {formatearCentavos(diferencia)}
            </dd>
          </div>
        </dl>

        <div className="flex gap-2">
          {soloLectura ? (
            comprobante?.estado === "contabilizado" && (
              <button
                type="button"
                onClick={revertir}
                disabled={ocupado}
                className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
              >
                {ocupado ? "Reversando…" : "Reversar"}
              </button>
            )
          ) : (
            <>
              <button
                type="button"
                onClick={() => guardar(false)}
                disabled={ocupado}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
              >
                Guardar borrador
              </button>
              <button
                type="button"
                onClick={() => guardar(true)}
                disabled={ocupado || !cuadra}
                title={cuadra ? undefined : "Los débitos y créditos deben ser iguales."}
                className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-600 disabled:opacity-50"
              >
                {ocupado ? "Procesando…" : "Contabilizar"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
