import { obtenerEmpresas } from "./api";
import type { Empresa } from "./types";

/**
 * Resuelve la empresa activa desde `?empresa=`; si no viene, usa la primera
 * registrada. Evita que cada vista repita la misma lógica de selección.
 */
export async function resolverEmpresa(
  parametro: string | string[] | undefined,
): Promise<{ empresa: Empresa | null; empresas: Empresa[] }> {
  const empresas = await obtenerEmpresas();
  if (empresas.length === 0) return { empresa: null, empresas };

  const valor = Array.isArray(parametro) ? parametro[0] : parametro;
  const id = valor ? Number(valor) : Number.NaN;
  const empresa = empresas.find((e) => e.id === id) ?? empresas[0];

  return { empresa, empresas };
}
