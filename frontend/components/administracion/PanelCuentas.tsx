"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormularioCuenta } from "@/components/administracion/FormularioCuenta";
import { BannerError, EstadoVacio, Etiqueta } from "@/components/ui/Avisos";
import { actualizarCuenta, crearCuenta } from "@/lib/api";
import { ApiError, mensajeDeError } from "@/lib/errors";
import type { Cuenta, Naturaleza } from "@/lib/types";

type Edicion = { tipo: "crear" } | { tipo: "editar"; cuenta: Cuenta } | null;

interface Props {
  empresaId: number;
  cuentas: Cuenta[];
}

export function PanelCuentas({ empresaId, cuentas }: Props) {
  const router = useRouter();
  const [edicion, setEdicion] = useState<Edicion>(null);
  const [error, setError] = useState<{ mensaje: string; codigo?: string } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  function reportar(e: unknown) {
    setError({ mensaje: mensajeDeError(e), codigo: e instanceof ApiError ? e.code : undefined });
  }

  async function guardar(datos: {
    codigo: string;
    nombre: string;
    naturaleza: Naturaleza;
    activa: boolean;
  }) {
    setError(null);
    setOcupado(true);
    try {
      if (edicion?.tipo === "editar") {
        // El código no se envía: no es editable.
        await actualizarCuenta(empresaId, edicion.cuenta.id, {
          nombre: datos.nombre,
          naturaleza: datos.naturaleza,
        });
      } else {
        await crearCuenta(empresaId, datos);
      }
      setEdicion(null);
      router.refresh();
    } catch (e) {
      reportar(e);
    } finally {
      setOcupado(false);
    }
  }

  async function alternarActiva(cuenta: Cuenta) {
    setError(null);
    setOcupado(true);
    try {
      await actualizarCuenta(empresaId, cuenta.id, { activa: !cuenta.activa });
      router.refresh();
    } catch (e) {
      reportar(e);
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
          + Nueva cuenta
        </button>
      ) : (
        <FormularioCuenta
          key={edicion.tipo === "editar" ? edicion.cuenta.id : "nueva"}
          valor={edicion.tipo === "editar" ? edicion.cuenta : undefined}
          ocupado={ocupado}
          onGuardar={guardar}
          onCancelar={() => setEdicion(null)}
        />
      )}

      {cuentas.length === 0 ? (
        <EstadoVacio
          titulo="El plan de cuentas está vacío"
          detalle="Cree la primera cuenta para poder registrar comprobantes."
        />
      ) : (
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Código</th>
                <th className="px-4 py-2 font-medium">Nombre</th>
                <th className="px-4 py-2 font-medium">Naturaleza</th>
                <th className="px-4 py-2 font-medium">Estado</th>
                <th className="px-4 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cuentas.map((cuenta) => (
                <tr key={cuenta.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2 font-mono">{cuenta.codigo}</td>
                  <td className="px-4 py-2">{cuenta.nombre}</td>
                  <td className="px-4 py-2 text-slate-600">{cuenta.naturaleza}</td>
                  <td className="px-4 py-2">
                    <Etiqueta estado={cuenta.activa ? "activa" : "inactiva"} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        onClick={() => setEdicion({ tipo: "editar", cuenta })}
                        disabled={ocupado}
                        className="text-slate-900 underline-offset-2 hover:underline disabled:opacity-50"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => alternarActiva(cuenta)}
                        disabled={ocupado}
                        className="text-slate-600 underline-offset-2 hover:underline disabled:opacity-50"
                      >
                        {cuenta.activa ? "Inactivar" : "Activar"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-sm text-slate-500">
        Las cuentas no se eliminan: se inactivan. Una cuenta inactiva deja de ofrecerse al
        registrar comprobantes, pero sus movimientos históricos siguen en el libro mayor.
      </p>
    </div>
  );
}
