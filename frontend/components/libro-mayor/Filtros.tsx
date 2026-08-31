"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { Cuenta } from "@/lib/types";

interface Props {
  empresaId: number;
  cuentas: Cuenta[];
  valores: { cuentaId?: string; desde?: string; hasta?: string };
}

/**
 * Los filtros escriben en la URL en lugar de mantener estado local: la página es
 * un Server Component que se vuelve a renderizar con los nuevos `searchParams`,
 * y la consulta queda en un enlace compartible.
 */
export function FiltrosLibroMayor({ empresaId, cuentas, valores }: Props) {
  const router = useRouter();
  const [cuentaId, setCuentaId] = useState(valores.cuentaId ?? "");
  const [desde, setDesde] = useState(valores.desde ?? "");
  const [hasta, setHasta] = useState(valores.hasta ?? "");

  function consultar() {
    const query = new URLSearchParams({
      empresa: String(empresaId),
      cuenta: cuentaId,
      desde,
      hasta,
    });
    router.push(`/libro-mayor?${query}`);
  }

  const completo = cuentaId !== "" && desde !== "" && hasta !== "";

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-md border border-slate-200 bg-white p-4">
      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">Cuenta</span>
        <select
          value={cuentaId}
          onChange={(e) => setCuentaId(e.target.value)}
          className="w-64 rounded-md border border-slate-300 px-3 py-2"
        >
          <option value="">Seleccione…</option>
          {cuentas.map((cuenta) => (
            <option key={cuenta.id} value={cuenta.id}>
              {cuenta.codigo} — {cuenta.nombre}
            </option>
          ))}
        </select>
      </label>

      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">Desde</span>
        <input
          type="date"
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2"
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block font-medium text-slate-700">Hasta</span>
        <input
          type="date"
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2"
        />
      </label>

      <button
        type="button"
        onClick={consultar}
        disabled={!completo}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
      >
        Consultar
      </button>
    </div>
  );
}
