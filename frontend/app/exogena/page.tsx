import { FormularioExogena } from "@/components/exogena/FormularioExogena";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { obtenerHistorialExogena, obtenerValoresUvt, urlArchivoExogena } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import { formatearCOP } from "@/lib/money";
import type { Empresa, ExogenaGeneracion, UvtValor } from "@/lib/types";

export default async function PaginaExogena({ searchParams }: PageProps<"/exogena">) {
  const params = await searchParams;

  let empresa: Empresa | null = null;
  let historial: ExogenaGeneracion[] = [];
  let valoresUvt: UvtValor[] = [];
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) {
      [historial, valoresUvt] = await Promise.all([
        obtenerHistorialExogena(empresa.id),
        obtenerValoresUvt(),
      ]);
    }
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Información exógena</h1>
        {empresa && (
          <p className="mt-1 text-sm text-slate-600">
            Informante: {empresa.razon_social} · NIT {empresa.nit}-{empresa.dv}
          </p>
        )}
      </div>

      {error && <BannerError mensaje={error} />}
      {!error && !empresa && <EstadoVacio titulo="No hay empresas registradas" />}

      {empresa && <FormularioExogena empresaId={empresa.id} valoresUvt={valoresUvt} />}

      <section className="space-y-3">
        <h2 className="font-medium">Historial de generaciones</h2>

        {historial.length === 0 ? (
          <EstadoVacio
            titulo="Sin generaciones previas"
            detalle="Cada archivo generado queda registrado aquí para re-descargarlo."
          />
        ) : (
          <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
            <table className="w-full min-w-[880px] text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Generada</th>
                  <th className="px-4 py-2 font-medium">Año</th>
                  <th className="px-4 py-2 text-right font-medium">Umbral UVT</th>
                  <th className="px-4 py-2 text-right font-medium">Umbral $</th>
                  <th className="px-4 py-2 text-right font-medium">Registros</th>
                  <th className="px-4 py-2 text-right font-medium">Total bruto</th>
                  <th className="px-4 py-2 font-medium">Excluidos</th>
                  <th className="px-4 py-2 font-medium">Archivo</th>
                </tr>
              </thead>
              <tbody>
                {historial.map((generacion) => (
                  <tr key={generacion.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-2 text-slate-600">
                      {new Date(generacion.created_at).toLocaleString("es-CO")}
                    </td>
                    <td className="px-4 py-2">{generacion.anio_gravable}</td>
                    <td className="px-4 py-2 text-right font-mono">{generacion.umbral_uvt}</td>
                    <td className="px-4 py-2 text-right font-mono">
                      {formatearCOP(generacion.umbral_pesos)}
                    </td>
                    <td className="px-4 py-2 text-right">{generacion.total_registros}</td>
                    <td className="px-4 py-2 text-right font-mono">
                      {formatearCOP(generacion.total_valor_bruto)}
                    </td>
                    <td className="px-4 py-2 text-slate-600">
                      {generacion.exclusiones.length === 0 ? (
                        "—"
                      ) : (
                        <span title={generacion.exclusiones.map((e) => `${e.tercero}: ${e.motivo}`).join("\n")}>
                          {generacion.exclusiones.length}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <a
                        href={urlArchivoExogena(generacion.id)}
                        className="text-slate-900 underline underline-offset-2"
                      >
                        Descargar
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
