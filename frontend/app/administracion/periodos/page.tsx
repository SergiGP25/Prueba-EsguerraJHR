import { PanelPeriodos } from "@/components/administracion/PanelPeriodos";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { obtenerPeriodos } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import type { Empresa, Periodo } from "@/lib/types";

export default async function AdministracionPeriodos({
  searchParams,
}: PageProps<"/administracion/periodos">) {
  const params = await searchParams;

  let empresa: Empresa | null = null;
  let periodos: Periodo[] = [];
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) periodos = await obtenerPeriodos(empresa.id);
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-4">
      {error && <BannerError mensaje={error} />}
      {!error && !empresa && <EstadoVacio titulo="No hay empresas registradas" />}
      {empresa && <PanelPeriodos empresaId={empresa.id} periodos={periodos} />}
    </div>
  );
}
