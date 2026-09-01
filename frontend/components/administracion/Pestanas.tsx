"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

const PESTANAS = [
  { href: "/administracion", etiqueta: "Cuentas" },
  { href: "/administracion/terceros", etiqueta: "Terceros" },
  { href: "/administracion/periodos", etiqueta: "Períodos" },
];

/**
 * Cada pestaña es una ruta propia para que su página resuelva en el servidor solo
 * los datos que necesita. El layout no recibe `searchParams`, así que la empresa se
 * lee aquí en cliente, igual que en la navegación principal.
 */
export function PestanasAdministracion() {
  const ruta = usePathname();
  const empresa = useSearchParams().get("empresa");

  const conEmpresa = (href: string) => (empresa ? `${href}?empresa=${empresa}` : href);

  return (
    <div className="flex gap-1 border-b border-slate-200 pb-3">
      {PESTANAS.map((pestana) => {
        // Coincidencia exacta: con `startsWith`, "Cuentas" quedaría activa en todas.
        const activo = ruta === pestana.href;
        return (
          <Link
            key={pestana.href}
            href={conEmpresa(pestana.href)}
            className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
              activo
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {pestana.etiqueta}
          </Link>
        );
      })}
    </div>
  );
}
