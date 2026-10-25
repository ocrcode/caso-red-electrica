"""
ejecutar_base.py — Resuelve el caso base, compara las versiones del modelo (V0–V4, Tabla 7 de la
memoria: coste, tiempo y tamaño), mide el efecto de cada hipótesis (Tabla 8) y guarda tablas
(Excel, CSV) y figuras (PNG) en ./resultados/.  Ejecutar:  python ejecutar_base.py
"""
import os
import time
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datos import escenario_base
from modelo import construir_modelo, resolver, resultados, tamano

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultados')
os.makedirs(OUT, exist_ok=True)

COL = {'D': '#2a78d6', 'A': '#eb6834', 'C': '#1baf7a', 'F': '#eda100',
       'B': '#e87ba4', 'E': '#6250d6', 'Bombeo': '#8a8984'}
NOMBRE = {'D': 'D nuclear', 'A': 'A térmica', 'C': 'C térmica', 'F': 'F térmica',
          'B': 'B hidráulica', 'E': 'E hidráulica'}
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#e4e3df', 'grid.linewidth': 0.6,
                     'axes.edgecolor': '#8a8984', 'axes.titleweight': 'bold'})


def figura_despacho(r, fichero, titulo):
    gen, b = r['gen'], r['bombeo'].sum(axis=1)
    orden = [g for g in ['D', 'A', 'C', 'F', 'B', 'E'] if g in gen.columns]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = gen.index
    base = pd.Series(0.0, index=x)
    for g in orden:
        ax.bar(x, gen[g], bottom=base, color=COL[g], width=0.86, label=NOMBRE[g],
               edgecolor='white', linewidth=1)
        base += gen[g]
    ax.bar(x, -b, color=COL['Bombeo'], width=0.86, label='Bombeo (consumo)', edgecolor='white', linewidth=1)
    ax.step(list(x) + [x[-1] + 1], list(r['demanda']) + [r['demanda'].iloc[-1]], where='post',
            color='#0b0b0b', lw=2, label='Demanda', transform=ax.transData)
    ax.plot(x, r['demanda'] * 1.15, color='#0b0b0b', lw=1, ls='--', label='Demanda + 15 %')
    ax.set_xticks(range(0, 24))
    ax.set_xlabel('Hora')
    ax.set_ylabel('MW')
    ax.set_title(titulo, loc='left')
    ax.legend(ncol=5, fontsize=8, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.13))
    fig.tight_layout()
    fig.savefig(fichero, dpi=160)
    plt.close(fig)


def figura_deposito(r, fichero):
    fig, ax = plt.subplots(figsize=(10, 3))
    for c in r['nivel'].columns:
        ax.plot(r['nivel'].index, r['nivel'][c], color=COL['D'], lw=2, marker='o', ms=4,
                label='Depósito' if c == 'S' else f'Depósito {c}')
    ax.axhspan(10, 20, color='#2a78d6', alpha=0.06)
    ax.axhline(10, color='#8a8984', lw=1, ls='--')
    ax.set_ylim(9.5, 20.5)
    ax.set_xticks(range(0, 25))
    ax.set_xlabel('Instante (h)')
    ax.set_ylabel('m de agua')
    ax.set_title('Nivel del depósito superior (límites medioambientales 10–20 m)', loc='left')
    fig.tight_layout()
    fig.savefig(fichero, dpi=160)
    plt.close(fig)


def figura_lineas(r, fichero):
    u = r['uso_lineas'].T * 100
    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(u.values, aspect='auto', cmap='Blues', vmin=0, vmax=100)
    ax.set_yticks(range(len(u.index)), u.index)
    ax.set_xticks(range(24))
    ax.set_xlabel('Hora')
    ax.grid(False)
    for i in range(u.shape[0]):
        for j in range(u.shape[1]):
            if u.values[i, j] >= 99.5:
                ax.text(j, i, '●', ha='center', va='center', color='white', fontsize=6)
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.set_label('% de capacidad usada')
    ax.set_title('Carga de las líneas (● = línea saturada)', loc='left')
    fig.tight_layout()
    fig.savefig(fichero, dpi=160)
    plt.close(fig)


def guardar_excel(r, fichero):
    with pd.ExcelWriter(fichero) as xw:
        pd.Series(r['costes']).to_frame('€').to_excel(xw, sheet_name='Costes')
        r['gen'].round(1).to_excel(xw, sheet_name='Generacion_MW')
        r['bombeo'].round(1).to_excel(xw, sheet_name='Bombeo_MW')
        r['estado'].to_excel(xw, sheet_name='Marcha')
        r['arranques'].to_excel(xw, sheet_name='Arranques')
        r['nivel'].round(3).to_excel(xw, sheet_name='Nivel_deposito_m')
        r['flujos'].round(1).to_excel(xw, sheet_name='Flujos_MW')
        (r['uso_lineas'] * 100).round(1).to_excel(xw, sheet_name='Uso_lineas_%')
        pd.DataFrame({'Demanda': r['demanda'], 'Reserva disponible': r['reserva'],
                      'Reserva exigida': r['reserva_req']}).round(1).to_excel(xw, sheet_name='Reserva')


VERSIONES = [
    ('V0 Base: red, reserva, curva nuclear convexa sin binarias', {}),
    ('V1 Sin red (nudo único)', dict(RED=False)),
    ('V2 Sin reserva', dict(RESERVA=0)),
    ('V3 Nuclear con SOS2 (binarias)', dict(FORZAR_SOS2=True)),
    ('V4 Bombeo limitado a la potencia de la central y sin turbinar a la vez', dict(PBOMBA={'B': 450.0, 'E': 400.0})),
]

# Sensibilidad a las hipótesis (memoria, apartado 7.6): cada fila cambia UNA hipótesis del caso base.
CARBON_A = {'A': 0.82, 'C': 0.49, 'F': 0.49, 'D': 0.012, 'B': 0.024, 'E': 0.024, 'Eólica': 0.011}
HIPOTESIS = [
    ('H4 Curva nuclear: coste medio', dict(LECTURA_CURVA_D='medio')),
    ('H4 Curva nuclear: coste total en k€/h (no convexa, SOS2)', dict(LECTURA_CURVA_D='total_k')),
    ('H2 Nivel inicial 15 m (cierre >= inicial)', dict(H0=15.0)),
    ('H2 Nivel inicial 20 m (cierre >= inicial)', dict(H0=20.0)),
    ('H2 Nivel inicial 15 m y cierre libre', dict(H0=15.0, CIERRE_DEPOSITO='libre')),
    ('H1 Un depósito por central', dict(DEPOSITO_COMPARTIDO=False)),
    ('H5 Día aislado: A y D en marcha a las 0 h', dict(CICLICO=False)),
    ('H5 Día aislado: todo parado a las 0 h', dict(CICLICO=False, U0={g: 0 for g in 'ACFDBE'})),
    ('Reserva hidráulica sólo con agua en el depósito', dict(RESERVA_HIDRO_SIN_AGUA=False)),
    ('H3 Central A de carbón (0,82 t/MWh)', dict(EMISION=CARBON_A)),
]


if __name__ == '__main__':
    d = escenario_base()
    m = construir_modelo(d)
    info = resolver(m)
    r = resultados(m, d)
    print('Caso base:', info)
    print({k: round(v) for k, v in r['costes'].items()})
    guardar_excel(r, os.path.join(OUT, 'caso_base.xlsx'))
    figura_despacho(r, os.path.join(OUT, 'fig_despacho_base.png'), 'Despacho horario óptimo — caso base')
    figura_deposito(r, os.path.join(OUT, 'fig_deposito_base.png'))
    figura_lineas(r, os.path.join(OUT, 'fig_lineas_base.png'))

    filas = []
    for nombre, cambios in VERSIONES:
        dd = escenario_base()
        dd.update(cambios)
        t0 = time.time()
        mm = construir_modelo(dd)
        tam = tamano(mm)                      # tamaño de cada versión (criterio de comparación, Tabla 7)
        ii = resolver(mm)
        seg = time.time() - t0
        fila = dict(Version=nombre, Estado=ii['estado'], Coste=ii['coste'], Segundos=round(seg, 2),
                    Variables=tam['variables'], Binarias=tam['binarias'], Restricciones=tam['restricciones'])
        if ii['coste'] is not None:
            rr = resultados(mm, dd)
            fila['Arranques'] = int(rr['arranques'].sum().sum())
            fila['Horas F'] = int(rr['estado']['F'].sum()) if 'F' in rr['estado'] else 0
            fila['Horas hidro'] = int(rr['estado'][[g for g in ['B', 'E'] if g in rr['estado']]].sum().sum())
            fila['MWh bombeados'] = round(rr['bombeo'].sum().sum())
            fila['Δ vs base (€)'] = round(ii['coste'] - r['costes']['total'])
        filas.append(fila)
        print(fila)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(os.path.join(OUT, 'versiones_modelo.csv'), index=False)
    print(tabla.to_string())

    # ---- Sensibilidad a las hipótesis
    filas = []
    for nombre, cambios in [('Caso base', {})] + HIPOTESIS:
        dd = escenario_base()
        dd.update(cambios)
        t0 = time.time()
        mm = construir_modelo(dd)
        ii = resolver(mm)
        seg = time.time() - t0
        rr = resultados(mm, dd)
        emis = sum(dd['EMISION'].get(g, 0) * rr['gen'][g].sum() for g in rr['gen'].columns)
        filas.append({'Hipótesis': nombre, 'Estado': ii['estado'], 'Coste': round(ii['coste']),
                      'Δ vs base (€)': round(ii['coste'] - r['costes']['total']),
                      'Δ %': round(100 * (ii['coste'] - r['costes']['total']) / r['costes']['total'], 1),
                      'Horas F': int(rr['estado']['F'].sum()),
                      'Horas hidro': int(rr['estado'][['B', 'E']].sum().sum()),
                      'MWh bombeados': round(rr['bombeo'].sum().sum()),
                      'D medio (MW)': round(rr['gen']['D'].mean()),
                      'Arranques': int(rr['arranques'].sum().sum()),
                      'CO2 (t)': round(emis), 'Segundos': round(seg, 2)})
        print(filas[-1])
    pd.DataFrame(filas).to_csv(os.path.join(OUT, 'hipotesis.csv'), index=False)
