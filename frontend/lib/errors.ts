/**
 * Normalización de errores del backend.
 *
 * La API responde en tres formas distintas y la interfaz necesita una sola:
 *  - Errores de dominio: `{ code, detail }` (p. ej. PARTIDA_DOBLE, PERIODO_CERRADO).
 *  - Errores HTTP simples: `{ detail: "texto" }` (404, 409 por duplicado).
 *  - Validación de FastAPI: `{ detail: [{ loc, msg }, ...] }`.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(mensaje: string, status: number, code?: string) {
    super(mensaje);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/** Traducciones de los códigos de dominio a mensajes accionables para el usuario. */
const MENSAJES: Record<string, string> = {
  PARTIDA_DOBLE: "El comprobante no cuadra: el total de débitos debe ser igual al de créditos.",
  LINEAS_INSUFICIENTES: "El comprobante debe tener al menos dos líneas contables.",
  DEBITO_Y_CREDITO: "Una línea no puede tener débito y crédito al mismo tiempo.",
  VALOR_INVALIDO: "Cada línea debe tener un débito o un crédito mayor a cero.",
  CUENTA_INACTIVA: "Hay una cuenta inactiva en el comprobante.",
  CUENTA_NO_ENCONTRADA: "Alguna cuenta seleccionada no existe en la empresa.",
  TERCERO_NO_ENCONTRADO: "Alguno de los terceros seleccionados no existe en la empresa.",
  PERIODO_CERRADO: "El período contable está cerrado; no admite movimientos.",
  PERIODO_YA_CERRADO: "El período ya estaba cerrado.",
  COMPROBANTE_PROTEGIDO: "Un comprobante contabilizado no puede modificarse. Use una reversión.",
  COMPROBANTE_YA_REVERSADO: "Este comprobante ya fue reversado.",
  REVERSION_ESTADO_INVALIDO: "Solo se puede reversar un comprobante contabilizado.",
  ESTADO_INVALIDO: "El comprobante no está en un estado que permita esta operación.",
  UVT_NO_DISPONIBLE: "No hay valor de UVT para ese año. Sincronícelo antes de generar el archivo.",
  NIT_DV_INVALIDO: "El NIT de la empresa no supera la validación del dígito de verificación.",
  RANGO_INVALIDO: "La fecha inicial no puede ser posterior a la final.",
};

interface DetalleValidacion {
  loc?: (string | number)[];
  msg?: string;
}

function textoDeDetalle(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const partes = (detail as DetalleValidacion[])
      .map((d) => {
        const campo = d.loc?.filter((p) => p !== "body").join(".");
        return campo ? `${campo}: ${d.msg ?? ""}` : d.msg;
      })
      .filter(Boolean);
    if (partes.length > 0) return partes.join(" · ");
  }
  return null;
}

/** Construye un ApiError a partir de una respuesta fallida, sea cual sea su forma. */
export async function desdeRespuesta(respuesta: Response): Promise<ApiError> {
  let cuerpo: unknown = null;
  try {
    cuerpo = await respuesta.json();
  } catch {
    // Respuesta sin JSON (p. ej. un 502 de un proxy): se usa el texto de estado.
  }

  const datos = (cuerpo ?? {}) as { code?: string; detail?: unknown };
  const code = typeof datos.code === "string" ? datos.code : undefined;
  const mensaje =
    (code && MENSAJES[code]) ||
    textoDeDetalle(datos.detail) ||
    `Error ${respuesta.status} al comunicarse con el servidor.`;

  return new ApiError(mensaje, respuesta.status, code);
}

/** Convierte cualquier excepción en un mensaje presentable. */
export function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Ocurrió un error inesperado.";
}
