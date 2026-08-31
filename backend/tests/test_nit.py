"""Dígito de verificación del NIT: regla 10 del enunciado."""

from __future__ import annotations

import pytest

from app.core.nit import calcular_dv, dv_valido, normalizar


@pytest.mark.parametrize(
    ("nit", "dv"),
    [
        ("890903938", "8"),  # Bancolombia, par público verificable
        ("900123456", "8"),
        ("800197268", "4"),
        ("830053105", "3"),
    ],
)
def test_calcular_dv_de_nits_conocidos(nit, dv):
    assert calcular_dv(nit) == dv


def test_acepta_nit_con_separadores():
    assert calcular_dv("890.903.938") == calcular_dv("890903938")


def test_dv_valido_distingue_pares_correctos_e_incorrectos():
    assert dv_valido("890903938", "8")
    assert not dv_valido("890903938", "1")


@pytest.mark.parametrize("entrada", ["", "sin-digitos", "1234567890123456"])
def test_entradas_invalidas_no_revientan(entrada):
    assert not dv_valido(entrada, "0")


def test_normalizar_conserva_solo_digitos():
    assert normalizar(" 900-123.456 ") == "900123456"
