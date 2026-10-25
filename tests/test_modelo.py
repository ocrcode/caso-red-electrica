"""
Pruebas automáticas del modelo (pytest). Repiten las comprobaciones principales de validacion.py
y fijan las cifras del caso base que cita la memoria, para detectar cualquier cambio involuntario.
GitHub las ejecuta en cada cambio (.github/workflows/python-package.yml).  En local:  pytest
"""
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from datos import escenario_base                                   # noqa: E402
from modelo import construir_modelo, resolver, resultados, tamano  # noqa: E402
import validacion                                                   # noqa: E402


def resolver_escenario(**cambios):
    d = escenario_base()
    d.update(cambios)
    m = construir_modelo(d)
    return d, m, resolver(m)


@pytest.fixture(scope='module')
def base():
    return resolver_escenario()


def test_coste_y_emisiones_del_caso_base(base):
    d, m, info = base
    assert info['estado'] == 'optimal'
    assert info['coste'] == pytest.approx(613800, abs=1)
    assert resultados(m, d)['costes']['emis_t'] == pytest.approx(27028, abs=1)


def test_tamano_del_caso_base():
    assert tamano(construir_modelo(escenario_base())) == dict(variables=1105, binarias=144, restricciones=698)


def test_balance_reserva_y_deposito(base):
    d, m, _ = base
    r = resultados(m, d)
    oferta = r['gen'].sum(axis=1) - r['bombeo'].sum(axis=1)
    assert (oferta - r['demanda']).abs().max() < 1e-6                 # (R1) balance del sistema
    assert (r['reserva'] - r['reserva_req']).min() >= -1e-6           # (R7) reserva del 15 %
    assert r['nivel'].min().min() >= d['HMIN'] - 1e-6                 # (R6) límites del depósito
    assert r['nivel'].iloc[-1].min() >= d['H0'] - 1e-6                # (R6) cierre del día


def test_versiones_del_modelo(base):
    coste = base[2]['coste']
    assert resolver_escenario(RED=False)[2]['coste'] == pytest.approx(590096, abs=1)       # V1
    assert resolver_escenario(RESERVA=0)[2]['coste'] <= coste + 1                           # V2
    assert resolver_escenario(FORZAR_SOS2=True)[2]['coste'] == pytest.approx(coste, abs=1)  # V3


def test_comprobaciones_de_validacion(base):
    """Las 14 comprobaciones de validacion.py (verificación, fuerza bruta y coherencia)."""
    d, m, info = base
    validacion.informe.clear()
    validacion.v1_v2(d, m, resultados(m, d))
    validacion.v3_fuerza_bruta(21)
    validacion.v3_fuerza_bruta(3)
    validacion.v4_versiones(info['coste'])
    fallos = [nombre for nombre, ok, _ in validacion.informe if not ok]
    assert len(validacion.informe) == 14 and not fallos, fallos
