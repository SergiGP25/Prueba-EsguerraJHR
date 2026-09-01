"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BannerError, EstadoVacio, Etiqueta } from "@/components/ui/Avisos";
import { cerrarPeriodo, crearPeriodo } from "@/lib/api";
import { ApiError, mensajeDeError } from "@/lib/errors";
import type { Periodo } from "@/lib/types";

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const etiquetaPeriodo = (p: Periodo) => `${p.anio}-${String(p.mes).padStart(2, "0")}`;

interface Props {
  empresaId: number;
  periodos: Periodo[];
}

export function PanelPeriodos({ empresaId, periodos }: Props) {
  const router = useRouter();
  // Solo una fila puede estar pidiendo confirmación a la vez.
  const [confirmando, setConfirmando] = useState<number | null>(null);
  const [error, setError] = useState<{ mensaje: string; codigo?: string } | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [anio, setAnio] = useState(String(new Date().getFullYear()));
  const [mes, setMes] = useState(String(new Date().getMonth() + 1));

  function reportar(e: unknown) {
    setError({ mensaje: mensajeDeError(e), codigo: e instanceof ApiError ? e.code : undefined });
  }

  async function crear() {
    setError(null);
    setAviso(null);
    setOcupado(true);
    try {
      await crearPeriodo(empresaId, { anio: Number(anio), mes: Number(mes) });
      setAviso(`Período ${anio}-${mes.padStart(2, "0")} creado.`);
      router.refresh();
    } catch (e) {
      reportar(e);
    } finally {
      setOcupado(false);
    }
  }

  async function confirmarCierre(periodo: Periodo) {
    setError(null);
    setAviso(null);
    setOcupado(true);
    try {
      await cerrarPeriodo(periodo.id);
      setAviso(`Período ${etiquetaPeriodo(periodo)} cerrado.`);
    } catch (e) {
      reportar(e);
    } finally {
      setConfirmando(null);
      setOcupado(false);
      // Refresca siempre: si el 409 fue porque ya estaba cerrado, la tabla estaba
      // desactualizada y así el mensaje y la pantalla vuelven a coincidir.
      router.refresh();
    }
  }

  return (
    <div className="space-y-4">
      {error && <BannerError mensaje={error.mensaje} codigo={error.codigo} />}
      {aviso && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {aviso}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 rounded-md border border-slate-200 bg-white p-4">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Año</span>
          <input
            type="number"
            min={2000}
            max={2100}
            value={anio}
            disabled={ocupado}
            onChange={(e) => setAnio(e.target.value)}
            className="w-28 rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          />
        </label>

        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Mes</span>
          <select
            value={mes}
            disabled={ocupado}
            onChange={(e) => setMes(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          >
            {MESES.map((nombre, indice) => (
              <option key={nombre} value={indice + 1}>
                {nombre}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={crear}
          disabled={ocupado}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          Crear período
        </button>
      </div>

      {periodos.length === 0 ? (
        <EstadoVacio
          titulo="No hay períodos"
          detalle="También se crean solos a partir de la fecha del primer comprobante del mes."
        />
      ) : (
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Período</th>
                <th className="px-4 py-2 font-medium">Estado</th>
                <th className="px-4 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {periodos.map((periodo) => (
                <tr key={periodo.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <span className="font-mono">{etiquetaPeriodo(periodo)}</span>
                    <span className="ml-2 text-slate-500">{MESES[periodo.mes - 1]}</span>
                  </td>
                  <td className="px-4 py-2">
                    <Etiqueta estado={periodo.estado} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    {periodo.estado === "cerrado" ? (
                      <span className="text-slate-400">—</span>
                    ) : confirmando === periodo.id ? (
                      <div className="flex flex-wrap items-center justify-end gap-3">
                        <span className="text-slate-700">
                          ¿Cerrar {etiquetaPeriodo(periodo)}? Después no se puede reabrir.
                        </span>
                        <button
                          type="button"
                          onClick={() => confirmarCierre(periodo)}
                          disabled={ocupado}
                          className="rounded-md bg-red-700 px-3 py-1.5 text-white hover:bg-red-600 disabled:opacity-50"
                        >
                          {ocupado ? "Cerrando…" : "Sí, cerrar"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmando(null)}
                          disabled={ocupado}
                          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 hover:bg-slate-50 disabled:opacity-50"
                        >
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmando(periodo.id)}
                        disabled={ocupado}
                        className="text-slate-900 underline-offset-2 hover:underline disabled:opacity-50"
                      >
                        Cerrar período
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-sm text-slate-500">
        Cerrar un período impide registrar y contabilizar comprobantes de ese mes, y no tiene
        vuelta atrás. Un error detectado después se corrige con una reversión registrada en un
        período abierto.
      </p>
    </div>
  );
}
