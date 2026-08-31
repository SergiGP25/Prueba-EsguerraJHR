/**
 * Aritmética monetaria en el cliente.
 *
 * Los montos viajan como string desde el backend. Para sumarlos en el navegador
 * se convierten a **centavos enteros**: un número entero en JavaScript es exacto
 * hasta 2^53, lo que cubre montos muy por encima de cualquier caso real, mientras
 * que sumar `0.1 + 0.2` en coma flotante no lo es.
 *
 * Regla: se calcula en centavos y se envía siempre string al backend.
 */

import type { Money } from "./types";

const PATRON_MONTO = /^\d+(\.\d{1,2})?$/;

/** Indica si el texto capturado por el usuario es un monto válido (máx. 2 decimales). */
export function esMontoValido(texto: string): boolean {
  return PATRON_MONTO.test(texto.trim());
}

/** Convierte "1000000.50" a 100000050 centavos. Devuelve 0 si el texto está vacío. */
export function aCentavos(texto: string): number {
  const limpio = texto.trim();
  if (limpio === "") return 0;
  if (!esMontoValido(limpio)) return Number.NaN;

  const [entero, decimales = ""] = limpio.split(".");
  const centavos = decimales.padEnd(2, "0").slice(0, 2);
  return Number(entero) * 100 + Number(centavos);
}

/** Convierte 100000050 centavos al string "1000000.50" que espera el backend. */
export function aMonto(centavos: number): Money {
  const negativo = centavos < 0;
  const absoluto = Math.abs(centavos);
  const entero = Math.floor(absoluto / 100);
  const resto = String(absoluto % 100).padStart(2, "0");
  return `${negativo ? "-" : ""}${entero}.${resto}`;
}

const FORMATO_COP = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Formatea un monto para mostrarlo. Solo para presentación: la conversión a
 * `number` es segura aquí porque el resultado no vuelve al backend.
 */
export function formatearCOP(monto: Money | number): string {
  const valor = typeof monto === "number" ? monto : Number(monto);
  if (Number.isNaN(valor)) return "—";
  return FORMATO_COP.format(valor);
}

/** Formatea centavos enteros directamente. */
export function formatearCentavos(centavos: number): string {
  return formatearCOP(centavos / 100);
}
