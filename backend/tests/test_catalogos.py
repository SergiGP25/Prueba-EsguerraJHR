"""Catálogos maestros: plan de cuentas y terceros.

Se prueba lo que el formulario de administración vuelve un camino habitual: duplicados,
edición parcial, aislamiento entre empresas y el dígito de verificación del NIT.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def otra_empresa(client):
    """Segunda empresa, para verificar que los catálogos no se cruzan."""
    return client.post(
        "/api/empresas",
        json={"nit": "901555444", "dv": "3", "razon_social": "Otra S.A.S."},
    ).json()


# --- Plan de cuentas ------------------------------------------------------


def test_crear_cuenta(client, empresa):
    respuesta = client.post(
        f"/api/empresas/{empresa.id}/cuentas",
        json={"codigo": "1110", "nombre": "Bancos", "naturaleza": "debito"},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["activa"] is True


def test_crear_cuenta_con_codigo_repetido_se_rechaza(client, empresa, cuentas):
    respuesta = client.post(
        f"/api/empresas/{empresa.id}/cuentas",
        json={"codigo": cuentas["1105"].codigo, "nombre": "Caja duplicada", "naturaleza": "debito"},
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "CUENTA_DUPLICADA"


def test_actualizar_cuenta_solo_cambia_lo_enviado(client, empresa, cuentas):
    caja = cuentas["1105"]
    respuesta = client.patch(
        f"/api/empresas/{empresa.id}/cuentas/{caja.id}",
        json={"nombre": "Caja general"},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Caja general"
    # El código es la clave del PUC: no se edita ni se pierde al actualizar el resto.
    assert cuerpo["codigo"] == "1105"
    assert cuerpo["naturaleza"] == "debito"
    assert cuerpo["activa"] is True


def test_inactivar_y_reactivar_una_cuenta(client, empresa, cuentas):
    ruta = f"/api/empresas/{empresa.id}/cuentas/{cuentas['1105'].id}"

    assert client.patch(ruta, json={"activa": False}).json()["activa"] is False
    assert client.patch(ruta, json={"activa": True}).json()["activa"] is True


def test_no_se_puede_editar_una_cuenta_de_otra_empresa(client, empresa, cuentas, otra_empresa):
    """El aislamiento lo garantiza la ruta anidada, no la confianza en el id."""
    respuesta = client.patch(
        f"/api/empresas/{otra_empresa['id']}/cuentas/{cuentas['1105'].id}",
        json={"nombre": "Intento de cambio"},
    )
    assert respuesta.status_code == 404


# --- Terceros -------------------------------------------------------------


def test_crear_tercero_calcula_el_dv_cuando_se_omite(client, empresa):
    respuesta = client.post(
        f"/api/empresas/{empresa.id}/terceros",
        json={"tipo_doc": "NIT", "num_doc": "890903938", "nombre": "Proveedor Nuevo S.A."},
    )
    assert respuesta.status_code == 201, respuesta.text
    # El usuario no tiene que conocer el algoritmo: lo aporta el sistema.
    assert respuesta.json()["dv"] == "8"


def test_crear_tercero_rechaza_un_dv_que_no_corresponde(client, empresa):
    respuesta = client.post(
        f"/api/empresas/{empresa.id}/terceros",
        json={"tipo_doc": "NIT", "num_doc": "890903938", "dv": "1", "nombre": "Datos Erróneos"},
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "TERCERO_DV_INVALIDO"
    # El mensaje dice cuál era el correcto, para que se pueda corregir sin calcularlo.
    assert "8" in respuesta.json()["detail"]


def test_documento_sin_dv_no_exige_digito(client, empresa):
    respuesta = client.post(
        f"/api/empresas/{empresa.id}/terceros",
        json={"tipo_doc": "CC", "num_doc": "1020304050", "nombre": "Persona Natural"},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["dv"] is None


def test_crear_tercero_duplicado_se_rechaza_con_409(client, empresa, tercero):
    """Antes chocaba contra la restricción de la base y salía como 500."""
    respuesta = client.post(
        f"/api/empresas/{empresa.id}/terceros",
        json={"tipo_doc": tercero.tipo_doc, "num_doc": tercero.num_doc, "nombre": "Repetido"},
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "TERCERO_DUPLICADO"


def test_actualizar_nombre_del_tercero(client, empresa, tercero):
    respuesta = client.patch(
        f"/api/empresas/{empresa.id}/terceros/{tercero.id}",
        json={"nombre": "Proveedor Ejemplo S.A.S. (corregido)"},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Proveedor Ejemplo S.A.S. (corregido)"
    assert cuerpo["num_doc"] == tercero.num_doc
    assert cuerpo["dv"] == tercero.dv


def test_cambiar_el_documento_recalcula_el_dv(client, empresa, tercero):
    """Conservar el DV anterior dejaría un par NIT/DV incoherente."""
    respuesta = client.patch(
        f"/api/empresas/{empresa.id}/terceros/{tercero.id}",
        json={"num_doc": "890903938"},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["dv"] == "8"


def test_no_se_puede_reasignar_el_documento_de_otro_tercero(client, empresa, tercero):
    otro = client.post(
        f"/api/empresas/{empresa.id}/terceros",
        json={"tipo_doc": "NIT", "num_doc": "890903938", "nombre": "Otro Proveedor"},
    ).json()

    respuesta = client.patch(
        f"/api/empresas/{empresa.id}/terceros/{otro['id']}",
        json={"num_doc": tercero.num_doc},
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "TERCERO_DUPLICADO"


def test_no_se_puede_editar_un_tercero_de_otra_empresa(client, empresa, tercero, otra_empresa):
    respuesta = client.patch(
        f"/api/empresas/{otra_empresa['id']}/terceros/{tercero.id}",
        json={"nombre": "Intento de cambio"},
    )
    assert respuesta.status_code == 404
