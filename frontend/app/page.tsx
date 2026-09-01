import Link from "next/link";

import { BannerError, EstadoVacio } from "@/components/ui/Avisos";
import { mensajeDeError } from "@/lib/errors";
import { resolverEmpresa } from "@/lib/empresa";

const SECCIONES = [
  {
    href: "/comprobantes",
    titulo: "Comprobantes",
    detalle: "Registrar borradores, contabilizar y reversar con trazabilidad.",
  },
  {
    href: "/libro-mayor",
    titulo: "Libro mayor",
    detalle: "Movimientos por cuenta y rango de fechas con saldo acumulado.",
  },
  {
    href: "/exogena",
    titulo: "Información exógena",
    detalle: "Generar el XML del año gravable y consultar el historial.",
  },
  {
    href: "/administracion",
    titulo: "Administración",
    detalle: "Plan de cuentas, terceros y cierre de períodos contables.",
  },
];

export default async function Inicio({ searchParams }: PageProps<"/">) {
  const params = await searchParams;

  let empresa = null;
  let error: string | null = null;
  try {
    ({ empresa } = await resolverEmpresa(params.empresa));
  } catch (e) {
    error = mensajeDeError(e);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Motor contable</h1>
        {empresa && (
          <p className="mt-1 text-sm text-slate-600">
            {empresa.razon_social} · NIT {empresa.nit}-{empresa.dv}
          </p>
        )}
      </div>

      {error && <BannerError mensaje={error} />}

      {!error && !empresa && (
        <EstadoVacio
          titulo="No hay empresas registradas"
          detalle="Ejecute el seed del backend para cargar la empresa de demostración."
        />
      )}

      {empresa && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SECCIONES.map((seccion) => (
            <Link
              key={seccion.href}
              href={`${seccion.href}?empresa=${empresa.id}`}
              className="rounded-lg border border-slate-200 bg-white p-5 transition-shadow hover:shadow-sm"
            >
              <h2 className="font-medium">{seccion.titulo}</h2>
              <p className="mt-1 text-sm text-slate-600">{seccion.detalle}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
