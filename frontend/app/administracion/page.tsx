import { PanelCuentas } from "@/components/administracion/PanelCuentas";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { obtenerCuentas } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import type { Cuenta, Empresa } from "@/lib/types";

export default async function AdministracionCuentas({ searchParams }: PageProps<"/administracion">) {
  const params = await searchParams;

  let empresa: Empresa | null = null;
  let cuentas: Cuenta[] = [];
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) cuentas = await obtenerCuentas(empresa.id);
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-4">
      {error && <BannerError mensaje={error} />}
      {!error && !empresa && <EstadoVacio titulo="No hay empresas registradas" />}
      {empresa && <PanelCuentas empresaId={empresa.id} cuentas={cuentas} />}
    </div>
  );
}
