"""
graficos.py — Figuras (matplotlib) de la herramienta y de la memoria.
Cada función recibe los resultados de modelo.resultados() y devuelve una figura.
"""
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COL = {'D': '#2a78d6', 'A': '#eb6834', 'C': '#1baf7a', 'F': '#eda100', 'B': '#e87ba4', 'E': '#6250d6',
       'Eólica': '#008300', 'Compra1': '#8a8984', 'Compra5': '#b8b7b2', 'Bombeo': '#8a8984', 'ENS': '#e34948'}
NOMBRE = {'D': 'D nuclear', 'A': 'A térmica', 'C': 'C térmica', 'F': 'F térmica', 'B': 'B hidráulica',
          'E': 'E hidráulica', 'Eólica': 'Eólica', 'Compra1': 'Compra nodo 1', 'Compra5': 'Compra nodo 5'}
plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.color': '#e4e3df', 'grid.linewidth': 0.6,
                     'axes.edgecolor': '#8a8984', 'axes.titleweight': 'bold', 'axes.titlelocation': 'left'})


def despacho(r, titulo='Producción por central y hora'):
    gen = r['gen']
    orden = [g for g in ['D', 'Eólica', 'A', 'C', 'F', 'B', 'E', 'Compra1', 'Compra5'] if g in gen.columns]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    x = gen.index
    base = pd.Series(0.0, index=x)
    for g in orden:
        ax.bar(x, gen[g], bottom=base, color=COL[g], width=0.86, label=NOMBRE[g], edgecolor='white', linewidth=0.8)
        base += gen[g]
    if len(r['ens'].columns) and r['ens'].values.sum() > 0.5:
        e = r['ens'].sum(axis=1)
        ax.bar(x, e, bottom=base, color='none', edgecolor=COL['ENS'], hatch='///', width=0.86,
               label='Demanda no servida')
    neg = r['bombeo'].sum(axis=1) + sum(-gen[c] for c in gen.columns if c.startswith('Venta'))
    ax.bar(x, -neg, color=COL['Bombeo'], width=0.86, label='Bombeo y venta (consumo)', edgecolor='white', linewidth=0.8)
    ax.step(list(x) + [x[-1] + 1], list(r['demanda']) + [r['demanda'].iloc[-1]], where='post',
            color='#0b0b0b', lw=1.8, label='Demanda')
    ax.set_xticks(range(0, 24))
    ax.set_xlabel('Hora')
    ax.set_ylabel('MW')
    ax.set_title(titulo)
    ax.legend(ncol=5, fontsize=7.5, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout()
    return fig


def deposito(r, d):
    fig, ax = plt.subplots(figsize=(10, 2.8))
    for c in r['nivel'].columns:
        ax.plot(r['nivel'].index, r['nivel'][c], lw=2, marker='o', ms=3, color=COL['D'],
                label='Depósito' if c == 'S' else f'Depósito {c}')
    ax.axhspan(d['HMIN'], d['HMAX'], color=COL['D'], alpha=0.06)
    ax.axhline(d['HMIN'], color='#8a8984', lw=1, ls='--')
    ax.set_ylim(d['HMIN'] - 0.5, d['HMAX'] + 0.5)
    ax.set_xticks(range(0, 25))
    ax.set_xlabel('Instante (h)')
    ax.set_ylabel('m de agua')
    ax.set_title(f"Nivel del depósito superior (límites {d['HMIN']:.0f}–{d['HMAX']:.0f} m)")
    fig.tight_layout()
    return fig


def reserva(r):
    fig, ax = plt.subplots(figsize=(10, 2.8))
    x = r['reserva'].index
    ax.bar(x, r['reserva'], color='#c3c2b7', width=0.86, label='Reserva disponible')
    ax.step(list(x) + [x[-1] + 1], list(r['reserva_req']) + [r['reserva_req'].iloc[-1]], where='post',
            color=COL['ENS'], lw=1.6, label='Reserva exigida')
    ax.set_xticks(range(0, 24))
    ax.set_xlabel('Hora')
    ax.set_ylabel('MW')
    ax.set_title('Reserva disponible frente a la exigida')
    ax.legend(fontsize=7.5, frameon=False, loc='upper left')
    fig.tight_layout()
    return fig


def lineas(r):
    u = r['uso_lineas'].T * 100
    fig, ax = plt.subplots(figsize=(10, 3.8))
    im = ax.imshow(u.values, aspect='auto', cmap='Blues', vmin=0, vmax=100)
    ax.set_yticks(range(len(u.index)), u.index)
    ax.set_xticks(range(u.shape[1]))
    ax.set_xlabel('Hora')
    ax.grid(False)
    for i in range(u.shape[0]):
        for j in range(u.shape[1]):
            if u.values[i, j] >= 99.5:
                ax.text(j, i, '●', ha='center', va='center', color='white', fontsize=6)
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.set_label('% de capacidad')
    ax.set_title('Carga de las líneas (● = saturada)')
    fig.tight_layout()
    return fig


def barrido(df, etiqueta_x, columna='coste (€)'):
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ok = df[df[columna].notna()] if columna in df else df.iloc[0:0]
    ax.plot(ok['valor'], ok[columna], marker='o', color=COL['D'], lw=2)
    if 'ENS (MWh)' in ok and (ok['ENS (MWh)'] > 0.5).any():
        mal = ok[ok['ENS (MWh)'] > 0.5]
        ax.scatter(mal['valor'], mal[columna], color=COL['ENS'], zorder=3, s=40, label='con demanda no servida')
        ax.legend(fontsize=7.5, frameon=False)
    ax.set_xlabel(etiqueta_x)
    ax.set_ylabel(columna)
    ax.set_title(f'{columna} según {etiqueta_x}')
    fig.tight_layout()
    return fig
