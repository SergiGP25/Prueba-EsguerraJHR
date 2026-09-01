"use client";

import { useState } from "react";

import type { Cuenta, Naturaleza } from "@/lib/types";

interface Props {
  /** Presente al editar; ausente al crear. */
  valor?: Cuenta;
  ocupado: boolean;
  onGuardar: (datos: { codigo: string; nombre: string; naturaleza: Naturaleza; activa: boolean }) => void;
  onCancelar: () => void;
}

export function FormularioCuenta({ valor, ocupado, onGuardar, onCancelar }: Props) {
  const editando = valor !== undefined;
  const [codigo, setCodigo] = useState(valor?.codigo ?? "");
  const [nombre, setNombre] = useState(valor?.nombre ?? "");
  const [naturaleza, setNaturaleza] = useState<Naturaleza>(valor?.naturaleza ?? "debito");
  const [activa, setActiva] = useState(valor?.activa ?? true);

  const completo = codigo.trim() !== "" && nombre.trim() !== "";

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onGuardar({ codigo: codigo.trim(), nombre: nombre.trim(), naturaleza, activa });
      }}
      className="flex flex-wrap items-end gap-3 rounded-md border border-slate-200 bg-white p-4"
    >
      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">Código</span>
        <input
          type="text"
          value={codigo}
          // Al editar queda deshabilitado: el backend no admite cambiar el código.
          disabled={editando || ocupado}
          placeholder="1110"
          onChange={(e) => setCodigo(e.target.value)}
          className="w-28 rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">Nombre</span>
        <input
          type="text"
          value={nombre}
          disabled={ocupado}
          placeholder="Bancos"
          onChange={(e) => setNombre(e.target.value)}
          className="w-64 rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">Naturaleza</span>
        <select
          value={naturaleza}
          disabled={ocupado}
          onChange={(e) => setNaturaleza(e.target.value as Naturaleza)}
          className="rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
        >
          <option value="debito">Débito</option>
          <option value="credito">Crédito</option>
        </select>
      </label>

      {!editando && (
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input
            type="checkbox"
            checked={activa}
            disabled={ocupado}
            onChange={(e) => setActiva(e.target.checked)}
            className="rounded border-slate-300"
          />
          <span className="font-medium text-slate-700">Activa</span>
        </label>
      )}

      <button
        type="submit"
        disabled={ocupado || !completo}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {ocupado ? "Guardando…" : editando ? "Guardar cambios" : "Crear cuenta"}
      </button>

      <button
        type="button"
        onClick={onCancelar}
        disabled={ocupado}
        className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
      >
        Cancelar
      </button>
    </form>
  );
}
