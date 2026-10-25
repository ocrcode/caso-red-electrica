"""
figuras_memoria.py — Figuras de los capítulos 2 y 4 de la memoria, generadas a partir de datos.py:

    resultados/figuras/fig1_esquema.png   Reformulación sintética del caso (Figura 1)
    resultados/figuras/fig2_demanda.png   Demanda horaria del sistema (Figura 2)
    resultados/figuras/fig3_red.png       Red y capacidad de las líneas (Figura 3)
    resultados/figuras/fig4_nuclear.png   Curva de la nuclear y sus tres lecturas (Figura 4)

El resto de figuras de resultados las generan ejecutar_base.py y analisis_sensibilidad.py.
Ejecutar:  python figuras_memoria.py
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import datos

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultados', 'figuras')
os.makedirs(OUT, exist_ok=True)

AZUL, AZUL_CLARO, GRIS, GRIS_CLARO, NEGRO = '#2a78d6', '#e3eefb', '#8a8984', '#c3c2b7', '#111111'
plt.rcParams.update({'font.family': ['Inter', 'DejaVu Sans'], 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False,
                     'axes.grid': True, 'axes.grid.axis': 'y', 'grid.color': '#e4e3df', 'grid.linewidth': 0.6,
                     'axes.edgecolor': GRIS, 'xtick.color': '#555555', 'ytick.color': '#555555',
                     'xtick.major.size': 0, 'ytick.major.size': 0})


def miles(x):
    """Formato español: 3.925 (punto de miles)."""
    return f'{x:,.0f}'.replace(',', '.')


def titular(fig, titulo, subtitulo):
    """Titular con la idea principal y subtítulo descriptivo, como en el resto de figuras."""
    fig.text(0.012, 0.975, titulo, fontsize=12.5, fontweight='bold', va='top', color=NEGRO)
    fig.text(0.012, 0.915, subtitulo, fontsize=9.5, va='top', color='#555555')


def guardar(fig, nombre):
    fig.savefig(os.path.join(OUT, nombre), dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- Figura 1: esquema del problema
def fig_esquema():
    fig = plt.figure(figsize=(8.4, 3.9))
    titular(fig, 'Cada día hay que decidir qué centrales arrancan y cómo se reparte la energía',
            'Reformulación sintética del caso: datos, decisiones horarias, restricciones y objetivo')
    ax = fig.add_axes([0, 0, 1, 0.84])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis('off')

    def caja(x, y, w, h, titulo, lineas, destacada=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.4,rounding_size=1.2',
                                    fc=AZUL_CLARO if destacada else 'white',
                                    ec=AZUL if destacada else GRIS, lw=1.6 if destacada else 1))
        ax.text(x + w / 2, y + h - 2.6, titulo, ha='center', va='top', fontsize=10, fontweight='bold')
        for i, t in enumerate(lineas):
            ax.text(x + 1.8, y + h - 8.3 - i * 4.6, t, ha='left', va='top', fontsize=8.3, color='#333333')

    caja(1, 6, 28, 50, 'Datos del enunciado',
         ['Demanda horaria de 5 centros', '6 centrales: límites y costes', 'Curva de coste de la nuclear',
          'Depósito de 10 a 20 m, bombeo', 'Red de 13 líneas y 2 conexiones', 'Reserva del 15 % cada hora',
          'Lagunas: hipótesis H1 a H9'])
    caja(36, 6, 28, 50, 'Decisiones (24 horas)',
         ['Qué centrales funcionan: u', 'Arranques: s', 'Potencia de cada central: p',
          'Bombeo y turbinado: b, u', 'Flujo por cada línea: f', 'Compra y venta exterior: c, v'], destacada=True)
    caja(71, 33, 28, 23, 'Objetivo',
         ['Mínimo coste diario de operación', 'Emisiones como segundo', 'objetivo (frontera de Pareto)'])
    caja(71, 3, 28, 26, 'Restricciones',
         ['Balance de potencia en cada nodo', 'Capacidad de las líneas',
          'Límites técnicos y depósito', 'Reserva del 15 %'])
    for y0, y1 in [(31, 31)]:
        ax.annotate('', xy=(35.3, y1), xytext=(29.8, y0),
                    arrowprops=dict(arrowstyle='-|>', color=GRIS, lw=1.4, mutation_scale=14))
    ax.annotate('', xy=(70.3, 44), xytext=(64.7, 37), arrowprops=dict(arrowstyle='-|>', color=GRIS, lw=1.4,
                                                                       mutation_scale=14))
    ax.annotate('', xy=(70.3, 16), xytext=(64.7, 23), arrowprops=dict(arrowstyle='-|>', color=GRIS, lw=1.4,
                                                                       mutation_scale=14))
    guardar(fig, 'fig1_esquema.png')


# ---------------------------------------------------------------- Figura 2: demanda horaria
def fig_demanda():
    d = datos.escenario_base()
    dtot = [sum(d['DMAX'].values()) * p / 100 for p in d['PERFIL']]
    cap = sum(d['PMAX'].values()) + sum(d['PH'].values())
    imin, imax = dtot.index(min(dtot)), dtot.index(max(dtot))
    fig = plt.figure(figsize=(8.4, 4.275))
    titular(fig, f'La demanda oscila entre {miles(dtot[imin])} MW a las {imin} h y '
                 f'{miles(dtot[imax])} MW a las {imax} h',
            'Demanda horaria del sistema (suma de los 5 centros), MW')
    ax = fig.add_axes([0.07, 0.13, 0.91, 0.66])
    colores = [AZUL if h in (imin, imax) else GRIS_CLARO for h in range(24)]
    ax.bar(range(24), dtot, color=colores, width=0.78, zorder=2)
    for h in (imin, imax):
        ax.text(h, dtot[h] + 60, miles(dtot[h]), ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.plot(range(24), [x * (1 + d['RESERVA']) for x in dtot], color=GRIS, ls=':', lw=1.2, zorder=3)
    ax.text(0.2, 4600, f"Demanda + {d['RESERVA'] * 100:.0f} % de reserva", fontsize=8.5, color='#555555')
    ax.axhline(cap, color=GRIS, ls='--', lw=1.2, zorder=1)
    ax.text(23.4, cap + 50, f'Capacidad instalada {miles(cap)} MW', ha='right', va='bottom', fontsize=8.5,
            color='#555555')
    ax.set_xticks(range(24))
    ax.set_xlim(-0.6, 23.6)
    ax.set_ylim(0, 5150)
    ax.set_xlabel('Hora del día', color='#555555')
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: miles(v)))
    guardar(fig, 'fig2_demanda.png')


# ---------------------------------------------------------------- Figura 3: red
POS = {5: (40, 90), 'F': (69, 90), 'A': (12, 70), 4: (37, 70), 'E': (56, 70), 3: (75, 59),
       'D': (45, 54), 1: (22, 44), 'C': (67, 40), 'B': (35, 29), 2: (52, 29)}
ETIQ_DEM = {5: (-9, 3.5), 4: (-4.5, -6.5), 3: (7.5, 0), 1: (-8, 0), 2: (0, -7.5)}


def fig_red():
    d = datos.escenario_base()
    tipo = {g: 'térmica' for g in d['TERMICAS']}
    tipo.update({g: 'nuclear' for g in d['NUCLEAR']})
    tipo.update({g: 'hidráulica' for g in d['HIDRO']})
    pot = dict(d['PMAX'])
    pot.update(d['PH'])
    # central que no puede evacuar su potencia máxima por sus líneas
    evac = {g: sum(c for l, c in d['CAP_LINEA'].items() if d['LINEAS'][l][0] == g) for g in pot}
    limitada = [g for g in pot if evac[g] < pot[g]]
    g0 = limitada[0] if limitada else None
    fig = plt.figure(figsize=(8.4, 5.4))
    titular(fig, (f'{g0} no puede evacuar sus {miles(pot[g0])} MW: sus dos líneas suman {miles(evac[g0])} MW'
                  if g0 else 'Red del sistema'),
            'Red del enunciado: centrales (cajas), centros de transformación (círculos, demanda máxima) '
            'y capacidad de cada línea en MW')
    ax = fig.add_axes([0, 0, 1, 0.86])
    ax.set_xlim(0, 100)
    ax.set_ylim(15, 100)
    ax.axis('off')
    ax.grid(False)
    for l, (i, j) in d['LINEAS'].items():
        (x0, y0), (x1, y1) = POS[i], POS[j]
        dest = i == g0
        ax.plot([x0, x1], [y0, y1], color=AZUL if dest else GRIS_CLARO, lw=2.2 if dest else 1.2, zorder=1)
        # etiqueta en el centro del tramo visible (entre el borde de la caja y el del círculo)
        dx, dy = x1 - x0, y1 - y0
        t0 = min(8.6 / abs(dx) if dx else 9e9, 4.2 / abs(dy) if dy else 9e9)
        t1 = 1 - 3.4 / (dx ** 2 + dy ** 2) ** 0.5
        tm = (t0 + t1) / 2
        ax.text(x0 + tm * dx, y0 + tm * dy, miles(d['CAP_LINEA'][l]), ha='center', va='center', fontsize=8.5,
                fontweight='bold' if dest else 'normal', color=NEGRO if dest else '#555555', zorder=3,
                bbox=dict(fc='white', ec='none', pad=0.8))
    for g in pot:
        x, y = POS[g]
        dest = g == g0
        ax.add_patch(FancyBboxPatch((x - 8, y - 3.6), 16, 7.2, boxstyle='round,pad=0.3,rounding_size=1.2',
                                    fc=AZUL_CLARO if dest else 'white', ec=AZUL if dest else GRIS,
                                    lw=1.6 if dest else 1, zorder=4))
        ax.text(x, y + 1.1, f'{g} · {tipo[g]}', ha='center', va='center', fontsize=9, fontweight='bold', zorder=5)
        ax.text(x, y - 1.8, f'{miles(pot[g])} MW', ha='center', va='center', fontsize=8.5, color='#333333',
                zorder=5)
    for n, dmax in d['DMAX'].items():
        x, y = POS[n]
        ax.scatter([x], [y], s=520, facecolor='white', edgecolor=GRIS, linewidth=1, zorder=4)
        ax.text(x, y, str(n), ha='center', va='center', fontsize=10, fontweight='bold', zorder=5)
        dx, dy = ETIQ_DEM[n]
        ax.text(x + dx, y + dy, f'{miles(dmax)} MW', ha='center', va='center', fontsize=8.5, color='#555555')
    for n in d['NODOS_EXT']:
        x, y = POS[n]
        x0, y0 = (x, y + 8) if n == 5 else (x - 15, y - 12)
        ax.annotate('', xy=(x - (0 if n == 5 else 2.2), y + (3 if n == 5 else -2)), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='-|>', color=GRIS, lw=1, ls='--'))
        ax.text(x0 + (2 if n == 5 else -1), y0 - (1.5 if n == 5 else 3), 'Red exterior', fontsize=8.5,
                color='#555555', ha='left' if n == 5 else 'center')
    guardar(fig, 'fig3_red.png')


# ---------------------------------------------------------------- Figura 4: curva de la nuclear
def fig_nuclear():
    d = datos.escenario_base()
    lect = {'marginal': datos.curva_nuclear('marginal'), 'medio': datos.curva_nuclear('medio'),
            'total_k': datos.curva_nuclear('total_k')}
    ref = max(d['CEXTRA'].values())                  # coste extra de las térmicas (5 €/MWh)
    xs_m, ys_m = zip(*lect['marginal'])
    # MW extra a partir de los cuales el coste marginal de D supera al de las térmicas
    corte = next(y for x, y in sorted(datos.CURVA_D, key=lambda p: p[1]) if x >= ref)
    fig = plt.figure(figsize=(8.4, 4.6))
    titular(fig, f'Según la lectura de la curva, la nuclear a plena carga cuesta de '
                 f'{miles(ys_m[-1])} a {miles(lect["total_k"][-1][1])} €/h extra',
            'Coste extra sobre el mínimo (€/h) frente a los MW por encima de 500 MW, para las tres lecturas del eje X')
    ax = fig.add_axes([0.08, 0.12, 0.58, 0.68])
    ax.grid(axis='both')
    for clave, (texto, color, lw) in {'total_k': ('X = coste total (k€/h), no convexa', GRIS_CLARO, 1.4),
                                      'medio': ('X = coste medio (€/MWh)', GRIS_CLARO, 1.4),
                                      'marginal': ('X = coste marginal (€/MWh), caso base', AZUL, 2.2)}.items():
        xs, ys = zip(*lect[clave])
        ax.plot(xs, ys, color=color, lw=lw, marker='o', ms=4, zorder=3 if clave == 'marginal' else 2)
        ax.text(xs[-1] + 12, ys[-1], f'{texto} · {miles(ys[-1])}', va='center', fontsize=8.5,
                fontweight='bold' if clave == 'marginal' else 'normal', color=NEGRO if clave == 'marginal' else '#555555',
                clip_on=False)
    ax.plot([0, 500], [0, ref * 500], color=GRIS, ls='--', lw=1)
    ax.text(512, ref * 500 + 260, f'Referencia: térmica a {ref:.0f} €/MWh · {miles(ref * 500)}', va='center',
            fontsize=8.5, color='#555555', clip_on=False)
    ax.axvline(corte, color=GRIS, ls='--', lw=1)
    ax.text(corte - 8, 9700, f'{corte} MW extra: el marginal llega a {ref:.0f} €/MWh', ha='right', va='top',
            fontsize=8.5, color='#555555')
    ax.set_xlim(-5, 505)
    ax.set_ylim(-150, 10300)
    ax.set_xlabel('MW extra sobre el mínimo (500 MW)', color='#555555')
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: miles(v)))
    guardar(fig, 'fig4_nuclear.png')


if __name__ == '__main__':
    fig_esquema()
    fig_demanda()
    fig_red()
    fig_nuclear()
    print('Figuras guardadas en', OUT)
