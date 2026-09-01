import { PanelTerceros } from "@/components/administracion/PanelTerceros";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { obtenerTerceros } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import type { Empresa, Tercero } from "@/lib/types";

export default async function AdministracionTerceros({
  searchParams,
}: PageProps<"/administracion/terceros">) {
  const params = await searchParams;

  let empresa: Empresa | null = null;
  let terceros: Tercero[] = [];
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) terceros = await obtenerTerceros(empresa.id);
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-4">
      {error && <BannerError mensaje={error} />}
      {!error && !empresa && <EstadoVacio titulo="No hay empresas registradas" />}
      {empresa && <PanelTerceros empresaId={empresa.id} terceros={terceros} />}
    </div>
  );
}
