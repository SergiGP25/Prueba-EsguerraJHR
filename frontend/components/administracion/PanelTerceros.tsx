"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormularioTercero } from "@/components/administracion/FormularioTercero";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { actualizarTercero, crearTercero } from "@/lib/api";
import { ApiError, mensajeDeError } from "@/lib/errors";
import type { Tercero } from "@/lib/types";

type Edicion = { tipo: "crear" } | { tipo: "editar"; tercero: Tercero } | null;

interface Props {
  empresaId: number;
  terceros: Tercero[];
}

export function PanelTerceros({ empresaId, terceros }: Props) {
  const router = useRouter();
  const [edicion, setEdicion] = useState<Edicion>(null);
  const [error, setError] = useState<{ mensaje: string; codigo?: string } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function guardar(datos: {
    tipo_doc: string;
    num_doc: string;
    dv: string | null;
    nombre: string;
  }) {
    setError(null);
    setOcupado(true);
    try {
      if (edicion?.tipo === "editar") {
        await actualizarTercero(empresaId, edicion.tercero.id, datos);
      } else {
        await crearTercero(empresaId, datos);
      }
      setEdicion(null);
      router.refresh();
    } catch (e) {
      setError({ mensaje: mensajeDeError(e), codigo: e instanceof ApiError ? e.code : undefined });
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="space-y-4">
      {error && <BannerError mensaje={error.mensaje} codigo={error.codigo} />}

      {edicion === null ? (
        <button
          type="button"
          onClick={() => setEdicion({ tipo: "crear" })}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50"
        >
          + Nuevo tercero
        </button>
      ) : (
        <FormularioTercero
          key={edicion.tipo === "editar" ? edicion.tercero.id : "nuevo"}
          valor={edicion.tipo === "editar" ? edicion.tercero : undefined}
          ocupado={ocupado}
          onGuardar={guardar}
          onCancelar={() => setEdicion(null)}
        />
      )}

      {terceros.length === 0 ? (
        <EstadoVacio
          titulo="Aún no hay terceros"
          detalle="Los movimientos asociados a un tercero son los que alimentan la información exógena."
        />
      ) : (
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Tipo</th>
                <th className="px-4 py-2 font-medium">Documento</th>
                <th className="px-4 py-2 font-medium">Nombre o razón social</th>
                <th className="px-4 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {terceros.map((tercero) => (
                <tr key={tercero.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2 text-slate-600">{tercero.tipo_doc}</td>
                  <td className="px-4 py-2 font-mono">
                    {tercero.num_doc}
                    {tercero.dv && <span className="text-slate-500">-{tercero.dv}</span>}
                  </td>
                  <td className="px-4 py-2">{tercero.nombre}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => setEdicion({ tipo: "editar", tercero })}
                      disabled={ocupado}
                      className="text-slate-900 underline-offset-2 hover:underline disabled:opacity-50"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-sm text-slate-500">
        Los terceros no se eliminan porque sus movimientos ya están registrados. Si un
        documento quedó mal capturado, se corrige aquí y el DV se recalcula.
      </p>
    </div>
  );
}
