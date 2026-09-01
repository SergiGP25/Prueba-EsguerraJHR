"use client";

import { useState } from "react";

import type { Tercero } from "@/lib/types";

const TIPOS_DOC = ["NIT", "CC", "CE", "PAS"];

interface Props {
  valor?: Tercero;
  ocupado: boolean;
  onGuardar: (datos: { tipo_doc: string; num_doc: string; dv: string | null; nombre: string }) => void;
  onCancelar: () => void;
}

export function FormularioTercero({ valor, ocupado, onGuardar, onCancelar }: Props) {
  const editando = valor !== undefined;
  const [tipoDoc, setTipoDoc] = useState(valor?.tipo_doc ?? "NIT");
  const [numDoc, setNumDoc] = useState(valor?.num_doc ?? "");
  const [dv, setDv] = useState(valor?.dv ?? "");
  const [nombre, setNombre] = useState(valor?.nombre ?? "");

  const esNit = tipoDoc.toUpperCase() === "NIT";
  const completo = numDoc.trim() !== "" && nombre.trim() !== "";

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onGuardar({
          tipo_doc: tipoDoc,
          num_doc: numDoc.trim(),
          // Vacío significa "calcúlalo tú": el algoritmo DIAN vive solo en el backend.
          dv: esNit && dv.trim() !== "" ? dv.trim() : null,
          nombre: nombre.trim(),
        });
      }}
      className="space-y-2 rounded-md border border-slate-200 bg-white p-4"
    >
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Tipo</span>
          <select
            value={tipoDoc}
            disabled={ocupado}
            onChange={(e) => setTipoDoc(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          >
            {TIPOS_DOC.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Número de documento</span>
          <input
            type="text"
            value={numDoc}
            disabled={ocupado}
            placeholder="890903938"
            onChange={(e) => setNumDoc(e.target.value)}
            className="w-44 rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          />
        </label>

        {esNit && (
          <label className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">DV</span>
            <input
              type="text"
              value={dv}
              disabled={ocupado}
              maxLength={1}
              placeholder="auto"
              onChange={(e) => setDv(e.target.value)}
              className="w-16 rounded-md border border-slate-300 px-3 py-2 text-center disabled:bg-slate-100"
            />
          </label>
        )}

        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Nombre o razón social</span>
          <input
            type="text"
            value={nombre}
            disabled={ocupado}
            placeholder="Proveedor Ejemplo S.A.S."
            onChange={(e) => setNombre(e.target.value)}
            className="w-72 rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
          />
        </label>

        <button
          type="submit"
          disabled={ocupado || !completo}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {ocupado ? "Guardando…" : editando ? "Guardar cambios" : "Crear tercero"}
        </button>

        <button
          type="button"
          onClick={onCancelar}
          disabled={ocupado}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          Cancelar
        </button>
      </div>

      {esNit && (
        <p className="text-xs text-slate-500">
          Deje el DV vacío para que el sistema lo calcule. Si lo informa y no corresponde al
          NIT, se rechaza el registro.
        </p>
      )}
    </form>
  );
}
