import { ComprobanteForm } from "@/components/comprobantes/ComprobanteForm";
import { BannerError } from "@/components/ui/Avisos";
import { obtenerComprobante, obtenerCuentas, obtenerTerceros } from "@/lib/api";
import { resolverEmpresa } from "@/lib/empresa";
import { mensajeDeError } from "@/lib/errors";
import type { Comprobante, Cuenta, Tercero } from "@/lib/types";

export default async function DetalleComprobante({
  params,
  searchParams,
}: PageProps<"/comprobantes/[id]">) {
  const [{ id }, query] = await Promise.all([params, searchParams]);

  let comprobante: Comprobante | null = null;
  let cuentas: Cuenta[] = [];
  let terceros: Tercero[] = [];
  let error: string | null = null;

  try {
    comprobante = await obtenerComprobante(Number(id));
    const { empresa } = await resolverEmpresa(query.empresa ?? String(comprobante.empresa_id));
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
      <h1 className="text-2xl font-semibold tracking-tight">
        {comprobante?.estado === "borrador" ? "Editar borrador" : "Comprobante"}
      </h1>

      {error && <BannerError mensaje={error} />}

      {comprobante && (
        <ComprobanteForm
          empresaId={comprobante.empresa_id}
          cuentas={cuentas}
          terceros={terceros}
          comprobante={comprobante}
        />
      )}
    </div>
  );
}
