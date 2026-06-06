#!/usr/bin/env python3
"""
Cellsius H2 Aircraft Range Model — Interactive
===============================================
Physics (Breguet-style, constant-altitude cruise):

    R = (E_elec / (m_ac * g)) * eta_prop * (L/D)

Energy chain:
    E_elec = m_H2 * LHV_H2 * eta_fc
    m_H2   = eps_grav * budget_fc       (gravimetric tank efficiency)

Total flying mass:
    m_ac = m_base + m_fc + budget_fc + m_payload

Mass budget breakdown (defaults, from cellsius.aero):
    m_base    = 613 kg   airframe + 105 kW e-motor + prop + avionics (no FC, no tank)
    m_fc      = 180 kg   FC stack + compressor + humidifier + cooling + valves + DCDC
    budget_fc =  87 kg   tank + H2  (→ 5.2 kg H2 at ε=6 %)
    m_payload = 170 kg   2 pilots
    ─────────────────
    MTOW      = 1050 kg  (cellsius.aero)

Calibrated to cellsius.aero specs:
    GH2 (ε=6 %, L/D=8, η_prop=0.79) → 200 km  (website: 200 km Reichweite)
    LH2 (ε=15.0 %)                  → 500 km  (next FP goal)
"""

import matplotlib
matplotlib.use('MacOSX')
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import matplotlib.ticker as ticker
import numpy as np

# ── Physical constants ─────────────────────────────────────────────────────────
g      = 9.81    # m/s²
LHV_H2 = 33.33   # kWh/kg  lower heating value of hydrogen

# ── Fixed parameters ───────────────────────────────────────────────────────────
# From cellsius.aero: MTOW=1050 kg, H2=5.2 kg, range=200 km, cruise=162 km/h, 105 kW
# Reinforced airframe for 1050 kg MTOW; 2-seat aircraft
m_base    = 613.0   # kg  airframe + 105 kW e-motor + prop + avionics (no FC, no tank)
m_payload = 170.0   # kg  2 pilots
eta_prop  =   0.79  # motor × ESC × propeller

# ── Slider defaults (calibrated to Cellsius targets) ──────────────────────────
D0 = dict(
    budget_fc   =  87.0,   # kg   tank + H2  (→ 5.2 kg H2 at ε=6 %, MTOW=1050 kg)
    m_fc        = 180.0,   # kg   FC stack + BoP (105 kW system)
    L_D         =   8.0,   # –    lift-to-drag ratio (lower: larger/draggier H2 aircraft)
    eps_GH2_pct =   6.0,   # %    350-bar Type-IV CFRP  → 200 km
    eps_LH2_pct =  15.0,   # %    cryo vacuum vessel    → 500 km
    eta_fc_pct  =  52.0,   # %    LHV-based FC system efficiency
)

# Achievable ε windows (shading on sweep plot)
GH2_LO, GH2_HI = 0.030, 0.090   # 350-bar Type-IV CFRP
LH2_LO, LH2_HI = 0.080, 0.300   # cryogenic, prototype → mature


# ── Physics core ───────────────────────────────────────────────────────────────
def compute(budget_fc, m_fc, eps_GH2_pct, eps_LH2_pct, eta_fc_pct, L_D):
    eps_GH2 = eps_GH2_pct / 100.0
    eps_LH2 = eps_LH2_pct / 100.0
    eta_fc  = eta_fc_pct  / 100.0

    m_ac = m_base + m_fc + budget_fc + m_payload   # total flying mass

    def R(E_kWh):
        return (E_kWh * 3.6e6) / (m_ac * g) * eta_prop * L_D / 1e3

    R_GH2 = R(eps_GH2 * budget_fc * LHV_H2 * eta_fc)
    R_LH2 = R(eps_LH2 * budget_fc * LHV_H2 * eta_fc)

    # Sweep 1: ε varies, budget_fc and m_fc fixed
    eps_arr = np.linspace(0.005, 0.42, 500)
    R_eps   = R(eps_arr * budget_fc * LHV_H2 * eta_fc)

    # Sweep 2: m_fc varies → m_ac changes, fuel energy fixed
    mfc_arr   = np.linspace(80, 300, 400)
    mac_arr   = m_base + mfc_arr + budget_fc + m_payload
    R_GH2_mfc = (eps_GH2 * budget_fc * LHV_H2 * eta_fc * 3.6e6) / (mac_arr * g) * eta_prop * L_D / 1e3
    R_LH2_mfc = (eps_LH2 * budget_fc * LHV_H2 * eta_fc * 3.6e6) / (mac_arr * g) * eta_prop * L_D / 1e3

    return dict(
        R_GH2=R_GH2, R_LH2=R_LH2, m_ac=m_ac,
        eps_arr=eps_arr, R_eps=R_eps,
        mfc_arr=mfc_arr, R_GH2_mfc=R_GH2_mfc, R_LH2_mfc=R_LH2_mfc,
        m_fc=m_fc, budget_fc=budget_fc,
        m_H2_GH2=eps_GH2 * budget_fc,
        m_H2_LH2=eps_LH2 * budget_fc,
    )


# ── Colours ────────────────────────────────────────────────────────────────────
BG    = '#0a0f1e'
PANEL = '#111827'
GRID  = '#1e2d42'
TEXT  = '#d8e8f5'
C_GH2 = '#42A5F5'
C_LH2 = '#FF7043'
C_TGT = '#FFD54F'


# ── Figure layout ──────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 10))
fig.patch.set_facecolor(BG)

# Plots sit in the top 55 % of the figure (bottom=0.40, top=0.88)
ax1 = fig.add_axes([0.05, 0.40, 0.26, 0.47])
ax2 = fig.add_axes([0.38, 0.40, 0.27, 0.47])
ax3 = fig.add_axes([0.72, 0.40, 0.27, 0.47])

for ax in (ax1, ax2, ax3):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID)
    ax.grid(color=GRID, lw=0.6, alpha=0.8)


# ── ax1: bar chart ─────────────────────────────────────────────────────────────
c0 = compute(**D0)

bars = ax1.bar([0, 1], [c0['R_GH2'], c0['R_LH2']],
               color=[C_GH2, C_LH2], width=0.52, zorder=3, edgecolor='none')
for tgt in [200, 500]:
    ax1.axhline(tgt, color=C_TGT, ls='--', lw=0.9, alpha=0.6, zorder=1)

bar_labels = []
for bar, r in zip(bars, [c0['R_GH2'], c0['R_LH2']]):
    t = ax1.text(bar.get_x() + bar.get_width() / 2, r + 7,
                 f'{r:.0f} km', ha='center', va='bottom',
                 color=TEXT, fontsize=11, fontweight='bold', zorder=4)
    bar_labels.append(t)

ax1.set_xticks([0, 1])
ax1.set_xticklabels(["GH₂  350 bar\n(H2-Sling)", "LH₂  cryo\n(next FP)"], color=TEXT, fontsize=9)
ax1.set_ylabel('Range  [km]')
ax1.set_title('Range Comparison', fontsize=9, pad=5)
ax1.set_ylim(0, 700)
ax1.yaxis.set_major_locator(ticker.MultipleLocator(100))
ax1.text(0.97, 0.97, '── target', transform=ax1.transAxes,
         color=C_TGT, fontsize=7.5, ha='right', va='top')


# ── ax2: range vs ε ────────────────────────────────────────────────────────────
line_eps, = ax2.plot(c0['eps_arr'] * 100, c0['R_eps'], color=TEXT, lw=1.4, alpha=0.45, zorder=2)
ax2.fill_between(c0['eps_arr'] * 100, 0, c0['R_eps'],
                 where=(c0['eps_arr'] >= GH2_LO) & (c0['eps_arr'] <= GH2_HI),
                 alpha=0.38, color=C_GH2, zorder=3,
                 label=f"GH₂ achievable  ({GH2_LO*100:.0f}–{GH2_HI*100:.0f} %)")
ax2.fill_between(c0['eps_arr'] * 100, 0, c0['R_eps'],
                 where=(c0['eps_arr'] >= LH2_LO) & (c0['eps_arr'] <= LH2_HI),
                 alpha=0.38, color=C_LH2, zorder=3,
                 label=f"LH₂ achievable  ({LH2_LO*100:.0f}–{LH2_HI*100:.0f} %)")
dot_GH2, = ax2.plot([D0['eps_GH2_pct']], [c0['R_GH2']], 'o', color=C_GH2, ms=8, zorder=6)
dot_LH2, = ax2.plot([D0['eps_LH2_pct']], [c0['R_LH2']], 'o', color=C_LH2, ms=8, zorder=6)
ax2.axhline(500, color=C_TGT, ls='--', lw=0.9, alpha=0.75, label='500 km goal')
ax2.set_xlabel('Tank gravimetric efficiency  ε  [%]')
ax2.set_ylabel('Range  [km]')
ax2.set_title('Range vs. Tank Efficiency', fontsize=9, pad=5)
ax2.set_xlim(0, 42)
ax2.set_ylim(0, 1300)
ax2.legend(fontsize=7.5, facecolor='#0D1B2A', labelcolor=TEXT, edgecolor=GRID,
           framealpha=0.9, loc='upper left')


# ── ax3: range vs m_fc ─────────────────────────────────────────────────────────
line_mfc_GH2, = ax3.plot(c0['mfc_arr'], c0['R_GH2_mfc'], color=C_GH2, lw=2.0,
                          label=f"GH₂  (ε = {D0['eps_GH2_pct']:.1f} %)")
line_mfc_LH2, = ax3.plot(c0['mfc_arr'], c0['R_LH2_mfc'], color=C_LH2, lw=2.0,
                          label=f"LH₂  (ε = {D0['eps_LH2_pct']:.1f} %)")
vl_mfc = ax3.axvline(D0['m_fc'], color='white', ls=':', lw=1.0, alpha=0.55,
                      label=f"current  {D0['m_fc']:.0f} kg")
ax3.axhline(500, color=C_TGT, ls='--', lw=0.9, alpha=0.75, label='500 km goal')
dot_mfc_GH2, = ax3.plot([D0['m_fc']], [c0['R_GH2']], 'o', color=C_GH2, ms=7, zorder=5)
dot_mfc_LH2, = ax3.plot([D0['m_fc']], [c0['R_LH2']], 'o', color=C_LH2, ms=7, zorder=5)
ax3.set_xlabel('FC system mass  m_fc  [kg]')
ax3.set_ylabel('Range  [km]')
ax3.set_title('Range vs. FC System Mass', fontsize=9, pad=5)
ax3.set_xlim(80, 300)
ax3.set_ylim(0, 800)
ax3.legend(fontsize=7.5, facecolor='#0D1B2A', labelcolor=TEXT, edgecolor=GRID, framealpha=0.9)

# Status bar sits between title and plots
status = fig.text(0.5, 0.915, '', ha='center', color=TEXT, fontsize=8.5, family='monospace')


# ── Sliders ────────────────────────────────────────────────────────────────────
SH, SY = 0.022, [0.290, 0.230, 0.170]
SL_COL = [(0.22, 0.28), (0.62, 0.28)]

def make_slider_ax(col, row):
    x, w = SL_COL[col]
    a = fig.add_axes([x, SY[row], w, SH])
    a.set_facecolor(PANEL)
    return a

sl_bfc   = Slider(make_slider_ax(0, 0), 'Fuel budget [kg]', 40, 200, valinit=D0['budget_fc'],   color='#80CBC4')
sl_mfc   = Slider(make_slider_ax(0, 1), 'FC mass [kg]',    100, 280, valinit=D0['m_fc'],        color='#78909C')
sl_LD    = Slider(make_slider_ax(0, 2), 'L/D',               5,  16, valinit=D0['L_D'],         color='#81d4fa')
sl_eGH2  = Slider(make_slider_ax(1, 0), 'ε  GH₂  [%]',  1.0, 15.0, valinit=D0['eps_GH2_pct'], color=C_GH2)
sl_eLH2  = Slider(make_slider_ax(1, 1), 'ε  LH₂  [%]',  3.0, 35.0, valinit=D0['eps_LH2_pct'], color=C_LH2)
sl_etafc = Slider(make_slider_ax(1, 2), 'η_fc  [%]',      35,  70,  valinit=D0['eta_fc_pct'],  color='#ce93d8')

all_sliders = [sl_bfc, sl_mfc, sl_LD, sl_eGH2, sl_eLH2, sl_etafc]
for sl in all_sliders:
    sl.label.set_color(TEXT)
    sl.valtext.set_color(TEXT)
    sl.ax.set_xticks([])

ax_btn = fig.add_axes([0.44, 0.100, 0.12, 0.030])
ax_btn.set_facecolor(PANEL)
btn = Button(ax_btn, 'Reset defaults', color=PANEL, hovercolor='#1e3a5a')
btn.label.set_color(TEXT)

for x, lbl in [(0.22, 'Aircraft / aerodynamics'), (0.62, 'Hydrogen system')]:
    fig.text(x, 0.326, lbl, color=TEXT, fontsize=8.5, alpha=0.65, fontweight='bold')


# ── Redraw ─────────────────────────────────────────────────────────────────────
def redraw(_=None):
    c = compute(budget_fc=sl_bfc.val, m_fc=sl_mfc.val,
                eps_GH2_pct=sl_eGH2.val, eps_LH2_pct=sl_eLH2.val,
                eta_fc_pct=sl_etafc.val, L_D=sl_LD.val)

    for rect, r, txt in zip(bars, [c['R_GH2'], c['R_LH2']], bar_labels):
        rect.set_height(r)
        txt.set_position((rect.get_x() + rect.get_width() / 2, r + 7))
        txt.set_text(f'{r:.0f} km')
    ax1.set_ylim(0, max(c['R_GH2'], c['R_LH2']) * 1.24)

    line_eps.set_data(c['eps_arr'] * 100, c['R_eps'])
    dot_GH2.set_data([sl_eGH2.val], [c['R_GH2']])
    dot_LH2.set_data([sl_eLH2.val], [c['R_LH2']])
    for coll in list(ax2.collections):
        coll.remove()
    ax2.fill_between(c['eps_arr'] * 100, 0, c['R_eps'],
                     where=(c['eps_arr'] >= GH2_LO) & (c['eps_arr'] <= GH2_HI),
                     alpha=0.38, color=C_GH2, zorder=3)
    ax2.fill_between(c['eps_arr'] * 100, 0, c['R_eps'],
                     where=(c['eps_arr'] >= LH2_LO) & (c['eps_arr'] <= LH2_HI),
                     alpha=0.38, color=C_LH2, zorder=3)
    ax2.set_ylim(0, max(c['R_eps']) * 1.1)

    line_mfc_GH2.set_data(c['mfc_arr'], c['R_GH2_mfc'])
    line_mfc_LH2.set_data(c['mfc_arr'], c['R_LH2_mfc'])
    vl_mfc.set_xdata([c['m_fc'], c['m_fc']])
    dot_mfc_GH2.set_data([c['m_fc']], [c['R_GH2']])
    dot_mfc_LH2.set_data([c['m_fc']], [c['R_LH2']])
    line_mfc_GH2.set_label(f"GH₂  (ε = {sl_eGH2.val:.1f} %)")
    line_mfc_LH2.set_label(f"LH₂  (ε = {sl_eLH2.val:.1f} %)")
    ax3.set_ylim(0, max(np.max(c['R_GH2_mfc']), np.max(c['R_LH2_mfc'])) * 1.15)
    ax3.legend(fontsize=7.5, facecolor='#0D1B2A', labelcolor=TEXT, edgecolor=GRID, framealpha=0.9)

    m_H2_shown = c['m_H2_GH2']
    status.set_text(
        f"MTOW = {c['m_ac']:.0f} kg  "
        f"(airframe {m_base:.0f} + FC {sl_mfc.val:.0f} + tank+H₂ {sl_bfc.val:.0f} + 2 pilots {m_payload:.0f})   │   "
        f"H₂: {m_H2_shown:.1f} kg   │   "
        f"GH₂: {c['R_GH2']:.0f} km   │   "
        f"LH₂: {c['R_LH2']:.0f} km"
    )
    fig.canvas.draw_idle()


def reset(_):
    for sl, key in zip(all_sliders, ['budget_fc', 'm_fc', 'L_D', 'eps_GH2_pct', 'eps_LH2_pct', 'eta_fc_pct']):
        sl.set_val(D0[key])

for sl in all_sliders:
    sl.on_changed(redraw)
btn.on_clicked(reset)


# ── Title  (single line, well above plots) ─────────────────────────────────────
fig.suptitle('CELLSIUS  ·  Hydrogen Aircraft Range Model',
             fontsize=13, fontweight='bold', color=TEXT, y=0.970)

redraw()
plt.show()
