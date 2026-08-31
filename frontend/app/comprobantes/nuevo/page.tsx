import { ComprobanteForm } from "@/components/comprobantes/ComprobanteForm";
import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { obtenerCuentas, obtenerTerceros } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import type { Cuenta, Empresa, Tercero } from "@/lib/types";

/**
 * Server Component: resuelve empresa, cuentas y terceros en el servidor y se los
 * entrega al formulario como props. El cliente no necesita pedir catálogos.
 */
export default async function NuevoComprobante({ searchParams }: PageProps<"/comprobantes/nuevo">) {
  const params = await searchParams;

  let empresa: Empresa | null = null;
  let cuentas: Cuenta[] = [];
  let terceros: Tercero[] = [];
  let error: string | null = null;

  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
    if (empresa) {
      [cuentas, terceros] = await Promise.all([
        obtenerCuentas(empresa.id),
        obtenerTerceros(empresa.id),
      ]);
    }
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Nuevo comprobante</h1>

      {error && <BannerError mensaje={error} />}
      {!error && !empresa && <EstadoVacio titulo="No hay empresas registradas" />}

      {empresa && (
        <ComprobanteForm empresaId={empresa.id} cuentas={cuentas} terceros={terceros} />
      )}
    </div>
  );
}
