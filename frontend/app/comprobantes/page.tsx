import Link from "next/link";

import { BannerError, EstadoVacio, Etiqueta } from "@/components/ui/Avisos";
import { obtenerComprobantes } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import { formatearCOP } from "@/lib/money";
import type { Comprobante, Empresa } from "@/lib/types";

export default async function ListaComprobantes({ searchParams }: PageProps<"/comprobantes">) {
  const params = await searchParams;

  let empresa: Empresa | null = null;
  let comprobantes: Comprobante[] = [];
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) comprobantes = await obtenerComprobantes(empresa.id);
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Comprobantes</h1>
          {empresa && <p className="mt-1 text-sm text-slate-600">{empresa.razon_social}</p>}
        </div>
        {empresa && (
          <Link
            href={`/comprobantes/nuevo?empresa=${empresa.id}`}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-700"
          >
            Nuevo comprobante
          </Link>
        )}
      </div>

      {error && <BannerError mensaje={error} />}

      {!error && comprobantes.length === 0 && (
        <EstadoVacio
          titulo="Aún no hay comprobantes"
          detalle="Cree el primero para verlo reflejado en el libro mayor."
        />
      )}

      {comprobantes.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">N.º</th>
                <th className="px-4 py-2 font-medium">Fecha</th>
                <th className="px-4 py-2 font-medium">Descripción</th>
                <th className="px-4 py-2 font-medium">Estado</th>
                <th className="px-4 py-2 text-right font-medium">Débitos</th>
                <th className="px-4 py-2 text-right font-medium">Créditos</th>
              </tr>
            </thead>
            <tbody>
              {comprobantes.map((comprobante) => (
                <tr key={comprobante.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">
                    <Link
                      href={`/comprobantes/${comprobante.id}?empresa=${empresa!.id}`}
                      className="font-medium text-slate-900 underline-offset-2 hover:underline"
                    >
                      {comprobante.numero ?? "—"}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{comprobante.fecha}</td>
                  <td className="px-4 py-2">{comprobante.descripcion}</td>
                  <td className="px-4 py-2">
                    <Etiqueta estado={comprobante.estado} />
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {formatearCOP(comprobante.total_debito)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {formatearCOP(comprobante.total_credito)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
