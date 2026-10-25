"""
analisis_sensibilidad.py — Los cinco análisis de sensibilidad del enunciado (capítulo 8 de la memoria),
las condiciones de validez de la solución (apartado 10.4) y la frontera de Pareto coste–CO2 (capítulo 9).
Guarda tablas (CSV) y figuras (PNG) en resultados/sensibilidad/.

    python analisis_sensibilidad.py           # análisis 1–5 y condiciones de validez
    python analisis_sensibilidad.py pareto    # frontera de Pareto y precio del CO2
"""
import os
import copy
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from datos import escenario_base
import escenarios as esc

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultados', 'sensibilidad')
os.makedirs(OUT, exist_ok=True)
AZUL, GRIS, ROJO = '#2a78d6', '#8a8984', '#e34948'


def base():
    d = escenario_base()
    d['ENS'] = True
    return d


def correr(d):
    s = esc.resolver_escenario(d)
    k = s['k']
    return dict(coste=k['coste'], ens=k['ens_mwh'], rdef=k['deficit_reserva_max'], co2=k['co2_t'],
                compra=k['compra_mwh'], venta=k['venta_mwh'], arranques=k['arranques'],
                **{f'h_{g}': h for g, h in k['horas_marcha'].items()}), s


K0 = correr(base())[0]
print('Base', K0)


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, nombre), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- 1. Precios de compra y venta
def analisis_1():
    filas = []
    for tramo, horas in [('todo el día', list(range(24)))] + list(esc.TRAMOS.items()):
        # todo el día: de 0 a 30 €/MWh de euro en euro y algunos puntos más altos para ver dónde deja de comprarse
        precios = (list(np.arange(0, 30.5, 1.0)) + [35.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
                   if tramo == 'todo el día' else np.arange(0, 30.5, 2.0))
        for p in precios:
            d = base()
            d['INTERCAMBIO'] = True
            d['PRECIO_COMPRA'] = [float(p) if h in horas else 1e4 for h in range(24)]
            k, _ = correr(d)
            filas.append(dict(tramo=tramo, precio=p, **k))
    compra = pd.DataFrame(filas)
    compra['ahorro'] = K0['coste'] - compra['coste']
    compra.to_csv(os.path.join(OUT, 'a1_compra.csv'), index=False)
    filas = []
    for p in np.arange(0, 40.5, 2.0):
        d = base()
        d['INTERCAMBIO'] = True
        d['PRECIO_COMPRA'] = [1e4] * 24
        d['PRECIO_VENTA'] = [float(p)] * 24
        k, _ = correr(d)
        filas.append(dict(precio=p, **k))
    venta = pd.DataFrame(filas)
    venta['beneficio'] = K0['coste'] - venta['coste']
    venta.to_csv(os.path.join(OUT, 'a1_venta.csv'), index=False)

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    estilos = {'todo el día': (AZUL, '-'), 'Valle (0-7 h)': (GRIS, '--'),
               'Llano (8-11, 15-19 h)': (GRIS, '-.'), 'Punta (12-14, 20-23 h)': (GRIS, ':')}
    for tramo, g in compra[compra['precio'] <= 30].groupby('tramo', sort=False):
        c, ls = estilos[tramo]
        ax[0].plot(g['precio'], g['compra'], color=c, ls=ls, lw=2, label=tramo)
    ax[0].set_xlabel('Precio de compra (€/MWh)')
    ax[0].set_ylabel('MWh comprados al día')
    ax[0].set_title('1a. Energía comprada según el precio')
    ax[0].legend(fontsize=7.5, frameon=False)
    ax[1].plot(venta['precio'], venta['venta'], color=AZUL, lw=2, marker='o', ms=3)
    ax[1].set_xlabel('Precio de venta (€/MWh)')
    ax[1].set_ylabel('MWh vendidos al día')
    ax[1].set_title('1b. Energía vendida según el precio')
    guardar(fig, 'a1_precios.png')
    return compra, venta


# ---------------------------------------------------------------- 2. Costes de las centrales
def analisis_2():
    filas = []
    for tabla, centrales, factores in [('CMIN', 'ACFD', [0.5, 0.75, 1.25, 1.5]),
                                       ('CEXTRA', 'ACF', [0.5, 0.8, 0.9, 1.1, 1.2, 1.5]),
                                       ('CARR', 'ACFD', [0.0, 2.0, 5.0, 10.0])]:
        for g in centrales:
            for f in factores:
                d = base()
                d[tabla][g] = d[tabla][g] * f
                k, _ = correr(d)
                plan = ''.join(f"{c}{k[f'h_{c}']}" for c in 'ACFDBE')
                filas.append(dict(parametro=tabla, central=g, factor=f, plan=plan, **k))
    df = pd.DataFrame(filas)
    df['delta'] = df['coste'] - K0['coste']
    df['delta_pct'] = 100 * df['delta'] / K0['coste']
    df.to_csv(os.path.join(OUT, 'a2_costes.csv'), index=False)
    return df


# ---------------------------------------------------------------- 3. Capacidades y paradas
def analisis_3():
    filas = []
    for g in ['A', 'B', 'C', 'D', 'E', 'F']:
        d = base()
        d['INDISPONIBLES'] = [g]
        k, _ = correr(d)
        filas.append(dict(caso=f'Parada de {g}', **k))
    paradas = pd.DataFrame(filas)
    paradas['delta'] = paradas['coste'] - K0['coste']
    paradas.to_csv(os.path.join(OUT, 'a3_paradas.csv'), index=False)
    filas = []
    for g in 'ACFD':
        for f in [0.8, 0.9, 1.1, 1.2]:
            d = base()
            d['PMAX'][g] *= f
            d['PMIN'][g] = min(d['PMIN'][g], d['PMAX'][g])
            k, _ = correr(d)
            filas.append(dict(parametro='PMAX', central=g, factor=f, **k))
        for f in [0.5, 0.75, 1.25]:
            d = base()
            d['PMIN'][g] = min(d['PMIN'][g] * f, d['PMAX'][g])
            k, _ = correr(d)
            filas.append(dict(parametro='PMIN', central=g, factor=f, **k))
    lim = pd.DataFrame(filas)
    lim['delta'] = lim['coste'] - K0['coste']
    lim.to_csv(os.path.join(OUT, 'a3_limites.csv'), index=False)
    return paradas, lim


# ---------------------------------------------------------------- 4. Líneas
def precios_sombra_lineas():
    """Precio sombra de la capacidad de cada línea (O'Neill et al., 2005): se fijan las binarias en
    su valor óptimo, se resuelve el LP resultante y se suman, para las 24 h, los costes reducidos de
    los flujos que están en su cota. Resultado en € por MW adicional en todas las horas del día."""
    import pyomo.environ as pyo
    from modelo import construir_modelo, resolver
    d = escenario_base()
    m = construir_modelo(d)
    resolver(m)
    for v in m.component_data_objects(pyo.Var):
        if v.is_binary():
            val = round(v.value)
            v.domain = pyo.Reals
            v.fix(val)
    m.rc = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    pyo.SolverFactory('appsi_highs').solve(m)
    T = m._meta['T']
    out = {}
    for l in m.L:
        out[l] = sum(abs(m.rc.get(m.f[l, t], 0.0)) for t in T
                     if abs(abs(m.f[l, t].value) - pyo.value(m.CAP[l])) < 1e-6)
    return out


def analisis_4():
    d0 = escenario_base()
    filas = []
    for l in d0['LINEAS']:
        d = base()
        d['LINEAS_CORTADAS'] = [l]
        k, _ = correr(d)
        d = base()
        d['CAP_LINEA'][l] *= 1.25
        k2, _ = correr(d)
        filas.append(dict(linea=l, cap=d0['CAP_LINEA'][l], ens_corte=k['ens'], rdef_corte=k['rdef'],
                          coste_corte=k['coste'], ahorro_mas25=K0['coste'] - k2['coste'],
                          co2_mas25=k2['co2'], delta_co2_mas25=k2['co2'] - K0['co2']))
    lineas = pd.DataFrame(filas).sort_values('ens_corte', ascending=False)
    ps = precios_sombra_lineas()
    lineas['precio_sombra_lp'] = lineas['linea'].map(ps)          # €/MW·día con las binarias fijas
    lineas['ahorro_mas25_por_MW'] = lineas['ahorro_mas25'] / (0.25 * lineas['cap'])
    lineas.to_csv(os.path.join(OUT, 'a4_lineas.csv'), index=False)
    # Ampliación conjunta de las líneas más rentables: efecto en coste y emisiones (capítulo 9)
    conj = []
    for grupo in [['A4'], ['A4', 'F3'], ['A4', 'F3', 'A5'], ['A4', 'F3', 'A5', 'D4', 'C3']]:
        d = base()
        for l in grupo:
            d['CAP_LINEA'][l] *= 1.25
        k3, _ = correr(d)
        conj.append(dict(lineas='+'.join(grupo), coste=k3['coste'], ahorro=K0['coste'] - k3['coste'],
                         co2=k3['co2'], delta_co2=k3['co2'] - K0['co2'], horas_F=k3['h_F'],
                         horas_hidro=k3['h_B'] + k3['h_E']))
    pd.DataFrame(conj).to_csv(os.path.join(OUT, 'a4_ampliacion_conjunta.csv'), index=False)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    l1 = lineas.sort_values('ens_corte')
    ax[0].barh(l1['linea'], l1['ens_corte'], color=[ROJO if v > 0.5 else GRIS for v in l1['ens_corte']])
    ax[0].set_xlabel('Demanda no servida (MWh/día)')
    ax[0].set_title('4a. Corte de cada línea (N-1)')
    l2 = lineas.sort_values('ahorro_mas25')
    ax[1].barh(l2['linea'], l2['ahorro_mas25'], color=[AZUL if v > 1 else GRIS for v in l2['ahorro_mas25']])
    ax[1].set_xlabel('Ahorro diario (€)')
    ax[1].set_title('4b. Ahorro al ampliar la línea un 25 %')
    guardar(fig, 'a4_lineas.png')
    return lineas


# ---------------------------------------------------------------- 5. Eólica en lugar de la nuclear
def analisis_5():
    filas = []
    potencias = [0, 1000, 2000, 3000, 4000, 5000, 6000]
    for perfil, fc in esc.PERFILES_EOLICOS.items():
        for P in potencias:
            d = base()
            d['EOLICA'] = True
            d['P_EOLICA'] = float(P)
            d['PERFIL_EOLICO'] = fc
            k, s = correr(d)
            vertido, usada = 0.0, 0.0
            if s['r'] is not None and 'Eólica' in s['r']['gen']:
                usada = s['r']['gen']['Eólica'].sum()
                vertido = P * sum(fc) - usada
            filas.append(dict(perfil=perfil, fc_medio=float(np.mean(fc)), P=P, disponible=P * sum(fc),
                              usada=usada, vertido=vertido, **k))
    eo = pd.DataFrame(filas)
    eo['ahorro'] = K0['coste'] - eo['coste']                       # ahorro de operación frente a la nuclear
    eo['umbral_eur_MWh'] = eo['ahorro'] / eo['usada'].where(eo['usada'] > 0)   # coste máx. de la eólica
    eo['umbral_eur_MW_dia'] = eo['ahorro'] / eo['P'].where(eo['P'] > 0)
    eo.to_csv(os.path.join(OUT, 'a5_eolica.csv'), index=False)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for i, (perfil, g) in enumerate(eo.groupby('perfil', sort=False)):
        c = AZUL if i == 0 else GRIS
        ls = ['-', '--', ':', '-.'][i]
        ax[0].plot(g['P'], g['ens'], color=c, ls=ls, lw=2, marker='o', ms=3, label=perfil)
        ax[1].plot(g['P'], g['coste'], color=c, ls=ls, lw=2, marker='o', ms=3, label=perfil)
    ax[1].axhline(K0['coste'], color=ROJO, lw=1, ls='--', label='Coste con nuclear')
    ax[0].set_xlabel('Potencia eólica instalada (MW)')
    ax[0].set_ylabel('Demanda no servida (MWh/día)')
    ax[0].set_title('5a. Servicio sin la nuclear')
    ax[1].set_xlabel('Potencia eólica instalada (MW)')
    ax[1].set_ylabel('Coste de operación (€/día)')
    ax[1].set_title('5b. Coste sin la nuclear (sin penalizaciones)')
    ax[0].legend(fontsize=7, frameon=False)
    ax[1].legend(fontsize=7, frameon=False)
    guardar(fig, 'a5_eolica.png')
    return eo


# ---------------------------------------------------------------- 7. Condiciones de validez de la solución
def analisis_7():
    """¿Cuánto puede crecer la demanda antes de que el plan deje de ser factible?  Se multiplica la
    demanda de todos los nodos y horas por (1 + x) y se mide la reserva que falta y la demanda no servida."""
    filas = []
    for x in np.arange(0.0, 0.205, 0.01):
        d = base()
        d['PERFIL'] = [p * (1 + x) for p in d['PERFIL']]
        k, _ = correr(d)
        filas.append(dict(aumento_demanda=round(x, 2), **k))
    df = pd.DataFrame(filas)
    df['delta'] = df['coste'] - K0['coste']
    df.to_csv(os.path.join(OUT, 'a7_validez_demanda.csv'), index=False)
    return df


if __name__ == "__main__" and "pareto" not in __import__("sys").argv:
    a1c, a1v = analisis_1()
    print('A1 hecho')
    a2 = analisis_2()
    print('A2 hecho')
    a3p, a3l = analisis_3()
    print('A3 hecho')
    a4 = analisis_4()
    print('A4 hecho')
    a5 = analisis_5()
    print('A5 hecho')
    a7 = analisis_7()
    print('Condiciones de validez hechas')


# ---------------------------------------------------------------- 6. Frontera de Pareto coste-CO2 (impacto ambiental)
def analisis_6(npuntos=12):
    """Método de las restricciones (épsilon, sesión 020): minimizar coste con un tope de CO2
    cada vez más bajo, entre el óptimo de coste y el mínimo de emisiones."""
    supuestos = {'Térmicas de ciclo combinado': {}}
    filas = []
    for nombre, cambios in supuestos.items():
        d = escenario_base()
        d['EMISION'].update(cambios)
        k_cost, _ = correr(d)                       # extremo 1: mínimo coste
        d2 = copy.deepcopy(d)
        d2['PESO_CO2'] = 1000.0                     # extremo 2: mínimo CO2 (y, a igualdad, mínimo coste)
        k_co2, _ = correr(d2)
        for eps in np.linspace(k_cost['co2'], k_co2['co2'], npuntos):
            d3 = copy.deepcopy(d)
            d3['CO2_MAX'] = float(eps) + 1e-6
            k, _ = correr(d3)
            filas.append(dict(supuesto=nombre, tope=eps, **k))
        for precio in [0, 5, 10, 20, 50, 100]:     # precio del CO2 dentro del objetivo
            d4 = copy.deepcopy(d)
            d4['PRECIO_CO2'] = float(precio)
            k, _ = correr(d4)
            filas.append(dict(supuesto=nombre, precio_co2=precio, **k))
    df = pd.DataFrame(filas)
    df.to_csv(os.path.join(OUT, 'a6_pareto_co2.csv'), index=False)
    fr = df[df['tope'].notna()]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for i, (nombre, g) in enumerate(fr.groupby('supuesto', sort=False)):
        g = g.sort_values(['co2', 'coste'])
        g = g.round({'co2': 0}).drop_duplicates('co2')
        g = g.loc[[j for j in g.index if not ((g['co2'] < g.loc[j, 'co2'] - 1e-6) & (g['coste'] <= g.loc[j, 'coste'] + 1e-6)).any()]]
        c = AZUL if i == 0 else GRIS
        ax[0].plot(g['co2'], g['coste'], color=c, marker='o', ms=4, lw=2, label=nombre)
        coste_t = (g['coste'].diff() / -g['co2'].diff()).iloc[1:]
        ax[1].plot(g['co2'].iloc[1:], coste_t, color=c, marker='o', ms=4, lw=2, label=nombre)
    ax[0].set_xlabel('Emisiones (t CO₂-eq/día)')
    ax[0].set_ylabel('Coste de operación (€/día)')
    ax[0].set_title('6a. Frontera de Pareto coste–CO₂')
    ax[0].legend(fontsize=7.5, frameon=False)
    ax[1].set_xlabel('Emisiones (t CO₂-eq/día)')
    ax[1].set_ylabel('€ por tonelada evitada (tramo)')
    ax[1].set_title('6b. Coste marginal de reducir emisiones')
    guardar(fig, 'a6_pareto_co2.png')
    return df


if __name__ == '__main__' and 'pareto' in __import__('sys').argv:
    analisis_6()
