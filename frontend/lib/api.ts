/**
 * Cliente de la API contable: único punto del frontend que conoce la URL del backend.
 *
 * En el servidor (Server Components) se usa `API_URL`, que dentro de Docker apunta al
 * contenedor `backend`. En el navegador se usa `NEXT_PUBLIC_API_URL`, que apunta al
 * puerto publicado en la máquina del usuario.
 */

import { desdeRespuesta } from "./errors";
import type {
  Comprobante,
  ComprobantePayload,
  Cuenta,
  Empresa,
  ExogenaGeneracion,
  LibroMayor,
  Periodo,
  Tercero,
  UvtValor,
} from "./types";

export function urlBase(): string {
  const enServidor = typeof window === "undefined";
  const url = enServidor
    ? process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL
    : process.env.NEXT_PUBLIC_API_URL;
  return url ?? "http://localhost:8000";
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${urlBase()}/api${ruta}`, {
    headers: { "Content-Type": "application/json" },
    // Los datos contables cambian con cada operación: nunca se sirven de caché.
    cache: "no-store",
    ...init,
  });
  if (!respuesta.ok) throw await desdeRespuesta(respuesta);
  return respuesta.json() as Promise<T>;
}

const json = (cuerpo: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(cuerpo),
});

// --- Empresas, cuentas, terceros y períodos -------------------------------

export const obtenerEmpresas = () => pedir<Empresa[]>("/empresas");

export const obtenerCuentas = (empresaId: number) =>
  pedir<Cuenta[]>(`/empresas/${empresaId}/cuentas`);

export const obtenerTerceros = (empresaId: number) =>
  pedir<Tercero[]>(`/empresas/${empresaId}/terceros`);

export const obtenerPeriodos = (empresaId: number) =>
  pedir<Periodo[]>(`/empresas/${empresaId}/periodos`);

export const cerrarPeriodo = (periodoId: number) =>
  pedir<Periodo>(`/periodos/${periodoId}/cerrar`, { method: "POST" });

// --- Comprobantes ---------------------------------------------------------

export const obtenerComprobantes = (empresaId: number, limit = 50) =>
  pedir<Comprobante[]>(`/empresas/${empresaId}/comprobantes?limit=${limit}`);

export const obtenerComprobante = (id: number) => pedir<Comprobante>(`/comprobantes/${id}`);

export const crearComprobante = (empresaId: number, datos: ComprobantePayload) =>
  pedir<Comprobante>(`/empresas/${empresaId}/comprobantes`, json(datos));

export const actualizarComprobante = (id: number, datos: ComprobantePayload) =>
  pedir<Comprobante>(`/comprobantes/${id}`, {
    method: "PUT",
    body: JSON.stringify(datos),
  });

export const contabilizarComprobante = (id: number) =>
  pedir<Comprobante>(`/comprobantes/${id}/contabilizar`, { method: "POST" });

export const revertirComprobante = (id: number, datos?: { fecha?: string; descripcion?: string }) =>
  pedir<Comprobante>(`/comprobantes/${id}/revertir`, json(datos ?? {}));

// --- Libro mayor ----------------------------------------------------------

export const obtenerLibroMayor = (
  empresaId: number,
  params: { cuenta_id: number; fecha_desde: string; fecha_hasta: string },
) =>
  pedir<LibroMayor>(
    `/empresas/${empresaId}/libro-mayor?${new URLSearchParams({
      cuenta_id: String(params.cuenta_id),
      fecha_desde: params.fecha_desde,
      fecha_hasta: params.fecha_hasta,
    })}`,
  );

// --- Exógena y UVT --------------------------------------------------------

export const obtenerHistorialExogena = (empresaId?: number) =>
  pedir<ExogenaGeneracion[]>(
    empresaId ? `/exogena/historial?empresa_id=${empresaId}` : "/exogena/historial",
  );

export const obtenerValoresUvt = () => pedir<UvtValor[]>("/uvt");

export const sincronizarUvt = (anio: number) =>
  pedir<{ estado: string; detalle: string }>(`/uvt/sincronizar?anio=${anio}`, { method: "POST" });

/**
 * Genera la exógena y devuelve el XML como blob para descargarlo.
 * No usa `pedir` porque la respuesta es un archivo, no JSON.
 */
export async function generarExogena(datos: {
  empresa_id: number;
  anio_gravable: number;
  umbral_uvt: string;
}): Promise<{ blob: Blob; nombreArchivo: string; generacionId: string | null }> {
  const respuesta = await fetch(`${urlBase()}/api/exogena/generar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
    cache: "no-store",
  });
  if (!respuesta.ok) throw await desdeRespuesta(respuesta);

  const disposicion = respuesta.headers.get("content-disposition") ?? "";
  const coincidencia = disposicion.match(/filename="?([^"]+)"?/);
  return {
    blob: await respuesta.blob(),
    nombreArchivo: coincidencia?.[1] ?? `exogena_${datos.anio_gravable}.xml`,
    generacionId: respuesta.headers.get("x-generacion-id"),
  };
}

/** URL pública de re-descarga: el navegador la abre directamente. */
export const urlArchivoExogena = (generacionId: number) =>
  `${urlBase()}/api/exogena/historial/${generacionId}/archivo`;
