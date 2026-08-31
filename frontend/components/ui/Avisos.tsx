/** Componentes de presentación compartidos: error, vacío y carga. */

export function BannerError({ mensaje, codigo }: { mensaje: string; codigo?: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <p>{mensaje}</p>
      {codigo && (
        // El código crudo ayuda a correlacionar con los logs del backend.
        <p className="mt-1 font-mono text-xs text-red-600">{codigo}</p>
      )}
    </div>
  );
}

export function EstadoVacio({ titulo, detalle }: { titulo: string; detalle?: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <p className="font-medium text-slate-700">{titulo}</p>
      {detalle && <p className="mt-1 text-sm text-slate-500">{detalle}</p>}
    </div>
  );
}

export function Cargando({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div className="flex items-center gap-2 px-1 py-8 text-sm text-slate-500">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
      {texto}
    </div>
  );
}

const ESTILOS_ESTADO: Record<string, string> = {
  borrador: "bg-amber-100 text-amber-800",
  contabilizado: "bg-emerald-100 text-emerald-800",
  reversado: "bg-slate-200 text-slate-700",
  abierto: "bg-emerald-100 text-emerald-800",
  cerrado: "bg-slate-200 text-slate-700",
};

export function Etiqueta({ estado }: { estado: string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
        ESTILOS_ESTADO[estado] ?? "bg-slate-100 text-slate-700"
      }`}
    >
      {estado}
    </span>
  );
}
