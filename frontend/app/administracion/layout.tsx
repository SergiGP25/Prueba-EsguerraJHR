import { Suspense } from "react";

import { PestanasAdministracion } from "@/components/administracion/Pestanas";

export default function AdministracionLayout({ children }: LayoutProps<"/administracion">) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Administración</h1>
        <p className="mt-1 text-sm text-slate-600">
          Plan de cuentas, terceros y períodos contables.
        </p>
      </div>

      {/* Las pestañas leen la empresa de la URL en cliente, de ahí el Suspense. */}
      <Suspense fallback={<div className="h-10 border-b border-slate-200" />}>
        <PestanasAdministracion />
      </Suspense>

      {children}
    </div>
  );
}
