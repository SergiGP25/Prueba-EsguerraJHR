import { FiltrosLibroMayor } from "@/components/libro-mayor/Filtros";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { obtenerCuentas, obtenerLibroMayor } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import { formatearCOP } from "@/lib/money";
import type { Cuenta, Empresa, LibroMayor } from "@/lib/types";

const texto = (valor: string | string[] | undefined) =>
  Array.isArray(valor) ? valor[0] : valor;

export default async function PaginaLibroMayor({ searchParams }: PageProps<"/libro-mayor">) {
  const params = await searchParams;
  const cuentaId = texto(params.cuenta);
  const desde = texto(params.desde);
  const hasta = texto(params.hasta);

  let empresa: Empresa | null = null;
  let cuentas: Cuenta[] = [];
  let libro: LibroMayor | null = null;
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) {
      cuentas = await obtenerCuentas(empresa.id);
      if (cuentaId && desde && hasta) {
        libro = await obtenerLibroMayor(empresa.id, {
          cuenta_id: Number(cuentaId),
          fecha_desde: desde,
          fecha_hasta: hasta,
        });
      }
    }
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Libro mayor</h1>

      {empresa && (
        <FiltrosLibroMayor
          empresaId={empresa.id}
          cuentas={cuentas}
          valores={{ cuentaId, desde, hasta }}
        />
      )}

      {error && <BannerError mensaje={error} />}

      {!error && !libro && (
        <EstadoVacio
          titulo="Seleccione una cuenta y un rango de fechas"
          detalle="La consulta se refleja en la URL, así que puede compartirla."
        />
      )}

      {libro && libro.movimientos.length === 0 && (
        <EstadoVacio
          titulo="Sin movimientos en el rango"
          detalle={`${libro.cuenta.codigo} — ${libro.cuenta.nombre}, entre ${libro.fecha_desde} y ${libro.fecha_hasta}.`}
        />
      )}

      {libro && libro.movimientos.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-medium">
              {libro.cuenta.codigo} — {libro.cuenta.nombre}
              <span className="ml-2 text-sm font-normal text-slate-500">
                (naturaleza {libro.cuenta.naturaleza})
              </span>
            </h2>
            <p className="text-sm text-slate-600">
              Saldo inicial{" "}
              <span className="font-mono">{formatearCOP(libro.saldo_inicial)}</span>
            </p>
          </div>

          <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
            <table className="w-full min-w-[860px] text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Fecha</th>
                  <th className="px-4 py-2 font-medium">Comprobante</th>
                  <th className="px-4 py-2 font-medium">Descripción</th>
                  <th className="px-4 py-2 font-medium">Tercero</th>
                  <th className="px-4 py-2 text-right font-medium">Débito</th>
                  <th className="px-4 py-2 text-right font-medium">Crédito</th>
                  <th className="px-4 py-2 text-right font-medium">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {libro.movimientos.map((movimiento, indice) => (
                  <tr
                    key={`${movimiento.comprobante_id}-${indice}`}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-4 py-2 text-slate-600">{movimiento.fecha}</td>
                    <td className="px-4 py-2">{movimiento.numero ?? "—"}</td>
                    <td className="px-4 py-2">{movimiento.descripcion}</td>
                    <td className="px-4 py-2 text-slate-600">
                      {movimiento.tercero_nombre ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {formatearCOP(movimiento.debito)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">
                      {formatearCOP(movimiento.credito)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono font-medium">
                      {formatearCOP(movimiento.saldo)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="border-t border-slate-200 bg-slate-50 font-medium">
                <tr>
                  <td className="px-4 py-2" colSpan={4}>
                    Totales del rango
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {formatearCOP(libro.total_debito)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {formatearCOP(libro.total_credito)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono">
                    {formatearCOP(libro.saldo_final)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
