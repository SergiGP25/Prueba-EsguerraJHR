"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

const ENLACES = [
  { href: "/comprobantes", etiqueta: "Comprobantes" },
  { href: "/libro-mayor", etiqueta: "Libro mayor" },
  { href: "/exogena", etiqueta: "Exógena" },
  { href: "/administracion", etiqueta: "Administración" },
];

/**
 * La empresa seleccionada viaja en el query param `?empresa=`, no en un contexto de
 * React: así los Server Components pueden leerla y el enlace sigue siendo compartible.
 * La navegación se encarga de propagarla entre vistas.
 */
export function Navegacion() {
  const ruta = usePathname();
  const params = useSearchParams();
  const empresa = params.get("empresa");

  const conEmpresa = (href: string) => (empresa ? `${href}?empresa=${empresa}` : href);

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex w-full max-w-6xl items-center gap-6 px-4 py-4">
        <Link href={conEmpresa("/")} className="font-semibold tracking-tight">
          Motor contable
        </Link>
        <div className="flex gap-1">
          {ENLACES.map((enlace) => {
            const activo = ruta.startsWith(enlace.href);
            return (
              <Link
                key={enlace.href}
                href={conEmpresa(enlace.href)}
                className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                  activo
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {enlace.etiqueta}
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
