/**
 * Espejo de los esquemas del backend (`backend/app/schemas.py`).
 *
 * Los montos son `string`, no `number`: el backend los serializa así para que
 * JSON no los convierta a coma flotante y se pierda precisión.
 */

export type Naturaleza = "debito" | "credito";
export type EstadoPeriodo = "abierto" | "cerrado";
export type EstadoComprobante = "borrador" | "contabilizado" | "reversado";

/** Monto decimal exacto en formato "1000000.00". Nunca operar con él como número. */
export type Money = string;

export interface Empresa {
  id: number;
  nit: string;
  dv: string;
  razon_social: string;
  created_at: string;
}

export interface Cuenta {
  id: number;
  empresa_id: number;
  codigo: string;
  nombre: string;
  naturaleza: Naturaleza;
  activa: boolean;
}

export interface Periodo {
  id: number;
  empresa_id: number;
  anio: number;
  mes: number;
  estado: EstadoPeriodo;
}

export interface Tercero {
  id: number;
  empresa_id: number;
  tipo_doc: string;
  num_doc: string;
  dv: string | null;
  nombre: string;
}

export interface LineaContable {
  id: number;
  cuenta_id: number;
  tercero_id: number | null;
  debito: Money;
  credito: Money;
  descripcion: string | null;
}

export interface Comprobante {
  id: number;
  empresa_id: number;
  periodo_id: number;
  numero: number | null;
  fecha: string;
  descripcion: string;
  estado: EstadoComprobante;
  reversa_comprobante_id: number | null;
  lineas: LineaContable[];
  total_debito: Money;
  total_credito: Money;
}

export interface LineaPayload {
  cuenta_id: number;
  tercero_id?: number | null;
  debito: Money;
  credito: Money;
  descripcion?: string | null;
}

export interface ComprobantePayload {
  fecha: string;
  descripcion: string;
  lineas: LineaPayload[];
}

export interface MovimientoMayor {
  fecha: string;
  comprobante_id: number;
  numero: number | null;
  descripcion: string;
  tercero_nombre: string | null;
  debito: Money;
  credito: Money;
  saldo: Money;
}

export interface LibroMayor {
  cuenta: Cuenta;
  fecha_desde: string;
  fecha_hasta: string;
  saldo_inicial: Money;
  movimientos: MovimientoMayor[];
  total_debito: Money;
  total_credito: Money;
  saldo_final: Money;
}

export interface Exclusion {
  tercero: string;
  motivo: string;
  valor: Money;
}

export interface ExogenaGeneracion {
  id: number;
  empresa_id: number;
  anio_gravable: number;
  umbral_uvt: Money;
  valor_uvt: Money;
  umbral_pesos: Money;
  total_registros: number;
  total_valor_bruto: Money;
  total_retencion: Money;
  exclusiones: Exclusion[];
  nombre_archivo: string;
  created_at: string;
}

export interface UvtValor {
  anio: number;
  valor: Money;
  fuente: string;
  actualizado_en: string;
}
