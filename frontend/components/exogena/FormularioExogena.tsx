"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BannerError } from "@/components/ui/Avisos";
import { generarExogena, sincronizarUvt } from "@/lib/api";
import { ApiError, mensajeDeError } from "@/lib/errors";
import type { UvtValor } from "@/lib/types";

interface Props {
  empresaId: number;
  valoresUvt: UvtValor[];
}

export function FormularioExogena({ empresaId, valoresUvt }: Props) {
  const router = useRouter();
  const [anio, setAnio] = useState(String(new Date().getFullYear() - 1));
  const [umbral, setUmbral] = useState("100.00");
  const [error, setError] = useState<{ mensaje: string; codigo?: string } | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const uvtDelAnio = valoresUvt.find((v) => v.anio === Number(anio));

  function reportar(e: unknown) {
    setError({ mensaje: mensajeDeError(e), codigo: e instanceof ApiError ? e.code : undefined });
  }

  async function generar() {
    setError(null);
    setAviso(null);
    setOcupado(true);
    try {
      const { blob, nombreArchivo } = await generarExogena({
        empresa_id: empresaId,
        anio_gravable: Number(anio),
        umbral_uvt: umbral,
      });

      // Descarga en el navegador a partir del blob recibido.
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = nombreArchivo;
      enlace.click();
      URL.revokeObjectURL(url);

      setAviso(`Archivo ${nombreArchivo} generado y descargado.`);
      router.refresh();
    } catch (e) {
      reportar(e);
    } finally {
      setOcupado(false);
    }
  }

  async function sincronizar() {
    setError(null);
    setOcupado(true);
    try {
      await sincronizarUvt(Number(anio));
      // La sincronización corre en segundo plano: se refresca para ver el resultado.
      setAviso(`Sincronización de la UVT ${anio} encolada. Actualice en unos segundos.`);
      router.refresh();
    } catch (e) {
      reportar(e);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="space-y-4">
      {error && <BannerError mensaje={error.mensaje} codigo={error.codigo} />}
      {aviso && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {aviso}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3 rounded-md border border-slate-200 bg-white p-4">
        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Año gravable</span>
          <input
            type="number"
            value={anio}
            min={2000}
            max={2100}
            onChange={(e) => setAnio(e.target.value)}
            className="w-32 rounded-md border border-slate-300 px-3 py-2"
          />
        </label>

        <label className="text-sm">
          <span className="mb-1 block font-medium text-slate-700">Umbral (UVT)</span>
          <input
            inputMode="decimal"
            value={umbral}
            onChange={(e) => setUmbral(e.target.value)}
            className="w-32 rounded-md border border-slate-300 px-3 py-2 text-right"
          />
        </label>

        <button
          type="button"
          onClick={generar}
          disabled={ocupado}
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-600 disabled:opacity-50"
        >
          {ocupado ? "Generando…" : "Generar y descargar XML"}
        </button>

        <button
          type="button"
          onClick={sincronizar}
          disabled={ocupado}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
        >
          Sincronizar UVT
        </button>
      </div>

      <p className="text-sm text-slate-600">
        {uvtDelAnio ? (
          <>
            UVT {anio}: <span className="font-mono">{uvtDelAnio.valor}</span> (fuente{" "}
            {uvtDelAnio.fuente}). Umbral equivalente en pesos: se calcula en el backend al
            generar.
          </>
        ) : (
          <>
            No hay valor de UVT registrado para {anio}. Sincronícelo antes de generar el
            archivo.
          </>
        )}
      </p>
    </div>
  );
}
