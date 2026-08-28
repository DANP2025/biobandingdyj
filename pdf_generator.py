import sys
import subprocess
import os
import urllib.request

try:
    import kaleido
except ImportError:
    pass

from fpdf import FPDF
from io import BytesIO
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import time
import gc

if not os.path.exists("Agency.ttf"):
    try:
        urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/teko/Teko-Medium.ttf", "Agency.ttf")
    except:
        pass

try:
    pio.kaleido.scope.mathjax = None
    current_args = list(pio.kaleido.scope.chromium_args)
    flags = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process", "--disable-software-rasterizer"]
    for flag in flags:
        if flag not in current_args:
            current_args.append(flag)
    pio.kaleido.scope.chromium_args = tuple(current_args)
except Exception:
    pass

def safe_render_fig(fig):
    try:
        pio.kaleido.scope.mathjax = None
        current_args = list(pio.kaleido.scope.chromium_args)
        flags = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"]
        for flag in flags:
            if flag not in current_args:
                current_args.append(flag)
        pio.kaleido.scope.chromium_args = tuple(current_args)
    except:
        pass

    last_error = ""
    for attempt in range(3):
        try:
            gc.collect()
            time.sleep(0.5) 
            return fig.to_image(format="png", engine="kaleido", scale=1.5)
        except Exception as e:
            last_error = str(e)
            time.sleep(1.5)
    raise Exception(f"Kaleido Timeout/Crash: {last_error}")

def create_pdf(jug_sel, data_jug, df_filtrado, df_historico):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    
    # Redondeo Global
    for col in ['M.O', 'Gr.T', '% PHV', 'Edad_Decimal', 'Edad PHV']:
        if col in df_filtrado.columns:
            df_filtrado[col] = df_filtrado[col].round(2)
        if col in data_jug.columns:
            data_jug[col] = data_jug[col].round(2)
        if col in df_historico.columns:
            df_historico[col] = df_historico[col].round(2)
            
    if os.path.exists("Agency.ttf"):
        pdf.add_font("Agency", "", "Agency.ttf", uni=True)
        font_name = "Agency"
    else:
        font_name = "Arial"
    
    def add_page_header(title):
        pdf.add_page()
        try:
            pdf.image("logo.jpeg", x=175, y=10, w=25)
        except:
            pass
        pdf.set_font(font_name, "", 26)
        pdf.set_text_color(26, 91, 54)
        pdf.cell(0, 15, "Reporte Bio-Banding", ln=True, align="L")
        pdf.set_font(font_name, "", 20)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, title, ln=True, align="L")
        pdf.ln(5)

    # =========================================================
    # PÁGINA 1: PERFIL INDIVIDUAL
    # =========================================================
    add_page_header(f"Perfil Individual: {jug_sel}")
    
    url_foto = data_jug['URLFOTO'].values[0] if 'URLFOTO' in data_jug.columns and not data_jug.empty else None
    if pd.notna(url_foto):
        try:
            res = requests.get(url_foto, timeout=5)
            if res.status_code == 200:
                pdf.image(BytesIO(res.content), x=90, y=42, w=30) 
        except:
            pass

    pdf.set_y(80) 
    
    if not data_jug.empty:
        v_edad = f"{data_jug['Edad_Decimal'].values[0]:.2f}"
        if 'Edad PHV' in data_jug.columns:
            v_edad_phv = f"{data_jug['Edad PHV'].values[0]:.2f}"
        elif 'Edad Biológica' in data_jug.columns:
            v_edad_phv = f"{data_jug['Edad Biológica'].values[0]:.2f}"
        else:
            v_edad_phv = "--"
            
        v_etapa = "Normal" if data_jug['M.O'].values[0] >= 0 else "Tardía"
        v_alt = f"{data_jug['Altura de Pie '].values[0]:.1f}"
        v_peso = f"{data_jug['Peso'].values[0]:.2f}"
        grt = data_jug['Gr.T'].values[0]
        v_ritmo = f"{grt:.2f}" if pd.notna(grt) else "Sin datos"
        v_phv = data_jug['% PHV'].values[0] if pd.notna(data_jug['% PHV'].values[0]) else 0
        v_grt = grt if pd.notna(grt) else 0
    else:
        v_edad, v_edad_phv, v_etapa, v_alt, v_peso, v_ritmo, v_phv, v_grt = "--", "--", "--", "--", "--", "--", 0, 0

    def draw_kpi(x, y, label, value, font_size=10):
        pdf.set_xy(x, y)
        pdf.set_fill_color(248, 249, 250)
        pdf.set_draw_color(39, 174, 96) 
        pdf.cell(55, 18, "", border=1, fill=True)
        pdf.set_xy(x, y+2)
        pdf.set_font(font_name, "", 22)
        pdf.set_text_color(0,0,0)
        pdf.cell(55, 8, str(value), align="C")
        pdf.set_xy(x, y+10)
        pdf.set_font(font_name, "", font_size)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(55, 8, label, align="C")
        pdf.set_text_color(0, 0, 0)

    draw_kpi(15, 80, "EDAD CRONOLOGICA", v_edad)
    draw_kpi(77.5, 80, "EDAD PHV", v_edad_phv)
    draw_kpi(140, 80, "RITMO MADURATIVO", v_etapa)
    draw_kpi(15, 103, "TALLA (CM)", v_alt)
    draw_kpi(77.5, 103, "MASA CORPORAL", v_peso)
    draw_kpi(140, 103, "VELOCIDAD DE CRECIMIENTO (CM/A\xd1O)", v_ritmo, font_size=7.5)

    # FIX DE RENDERIZADO: Uso de 'Arial' para evitar que Kaleido colapse al no encontrar la fuente custom en Linux
    color_phv = "#2ECC71" if v_phv < 85 else ("#F1C40F" if v_phv < 95 else "#E74C3C")
    fig_g = go.Figure()
    fig_g.add_trace(go.Indicator(mode="gauge+number", value=v_phv, domain={'x': [0, 0.45], 'y': [0, 1]}, title={'text': "Estatus Madurativo<br>(%PAH)", 'font': {'size': 20, 'family': 'Arial'}}, gauge={'axis': {'range': [80, 100]}, 'bar': {'color': color_phv}}))
    fig_g.add_trace(go.Indicator(mode="gauge+number", value=v_grt, domain={'x': [0.55, 1], 'y': [0, 1]}, title={'text': "Velocidad de Crecimiento<br>(cm/año)", 'font': {'size': 20, 'family': 'Arial'}}, gauge={'axis': {'range': [0, 15]}, 'bar': {'color': "black"}, 'steps': [{'range': [0, 5], 'color': "#2ECC71"}, {'range': [5, 7.2], 'color': "#F1C40F"}, {'range': [7.2, 15], 'color': "#E74C3C"}]}))
    fig_g.update_layout(width=900, height=350, margin=dict(l=60, r=60, t=80, b=30), font=dict(family='Arial'))
    
    try:
        img_g_bytes = safe_render_fig(fig_g)
        pdf.image(BytesIO(img_g_bytes), x=10, y=128, w=190)
    except: pass

    df_hist_plot = df_historico[df_historico['Nombre y Apellido'] == jug_sel]
    if not df_hist_plot.empty:
        fig_hist = px.scatter(df_hist_plot, x='Edad_Decimal', y='Altura de Pie ', title="Cinética de Crecimiento vs. Edad Decimal")
        fig_hist.update_traces(marker=dict(size=20, color='#1E3A8A'))
        fig_hist.update_layout(width=960, height=400, title_x=0.5, plot_bgcolor='white', margin=dict(l=60, r=50, t=50, b=60), font=dict(size=16, family='Arial'))
        fig_hist.update_xaxes(showgrid=True, gridcolor='#EFEFEF', title="Edad Cronológica (Años)")
        fig_hist.update_yaxes(showgrid=True, gridcolor='#EFEFEF', title="Talla (cm)")
        
        try:
            img_hist_bytes = safe_render_fig(fig_hist)
            pdf.image(BytesIO(img_hist_bytes), x=10, y=200, w=190)
        except: pass

    # =========================================================
    # PÁGINA 2: MATRIZ PLANTEL
    # =========================================================
    add_page_header("Matriz Plantel")
    
    pdf.set_y(50)
    pdf.set_font(font_name, "", 14)
    pdf.set_text_color(26, 91, 54)
    pdf.cell(60, 6, "Ventana Crítica: Circa-PHV", border=0, align="C")
    pdf.cell(5, 6, "", border=0)
    pdf.cell(60, 6, "Estatus Madurativo: Pre-PHV", border=0, align="C")
    pdf.cell(5, 6, "", border=0)
    pdf.cell(60, 6, "Alerta Neuromuscular", border=0, ln=True, align="C")
    
    pdf.set_font(font_name, "", 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0,0,0)
    
    pdf.cell(45, 6, "Nombre", border=1, fill=True)
    pdf.cell(15, 6, "M.O", border=1, align="C", fill=True)
    pdf.cell(5, 6, "", border=0)
    pdf.cell(45, 6, "Nombre", border=1, fill=True)
    pdf.cell(15, 6, "% PAH", border=1, align="C", fill=True)
    pdf.cell(5, 6, "", border=0)
    pdf.cell(45, 6, "Nombre", border=1, fill=True)
    pdf.cell(15, 6, "Cm/Año", border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font(font_name, "", 12)
    df_t1 = df_filtrado.copy()
    df_t1['Abs_MO'] = df_t1['M.O'].abs()
    
    top_phv = df_t1.sort_values('Abs_MO').head(1)[['Nombre y Apellido', 'M.O']]
    top_siguen = df_filtrado[df_filtrado['M.O'] < 0].sort_values('Nombre y Apellido').head(1)[['Nombre y Apellido', '% PHV']]
    top_crec = df_filtrado.sort_values('Gr.T', ascending=False).head(1)[['Nombre y Apellido', 'Gr.T']]
    for i in range(1):
        n1 = str(top_phv.iloc[i,0])[:22] if i < len(top_phv) else ""
        val1 = top_phv.iloc[i,1] if i < len(top_phv) else np.nan
        v1 = f"{val1:.2f}" if pd.notna(val1) else ""
        
        n2 = str(top_siguen.iloc[i,0])[:22] if i < len(top_siguen) else ""
        val2 = top_siguen.iloc[i,1] if i < len(top_siguen) else np.nan
        v2 = f"{val2:.2f}" if pd.notna(val2) else ""
        
        n3 = str(top_crec.iloc[i,0])[:22] if i < len(top_crec) else ""
        val3 = top_crec.iloc[i,1] if i < len(top_crec) else np.nan
        v3 = f"{val3:.2f}" if pd.notna(val3) else ""
        
        pdf.cell(45, 6, n1, border=1)
        if v1 != "":
            if val1 < -2: pdf.set_fill_color(46, 204, 113); pdf.set_text_color(0,0,0)
            elif val1 < -1: pdf.set_fill_color(241, 196, 15); pdf.set_text_color(0,0,0)
            elif val1 < 1: pdf.set_fill_color(231, 76, 60); pdf.set_text_color(255,255,255)
            elif val1 < 2: pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255,255,255)
            else: pdf.set_fill_color(46, 204, 113); pdf.set_text_color(0,0,0)
            pdf.cell(15, 6, v1, border=1, align="C", fill=True)
        else:
            pdf.cell(15, 6, v1, border=1, align="C")
        pdf.set_fill_color(240, 240, 240); pdf.set_text_color(0, 0, 0)
        pdf.cell(5, 6, "", border=0)
        
        pdf.cell(45, 6, n2, border=1)
        if v2 != "":
            val_num = float(v2)
            if val_num < 85:
                pdf.set_fill_color(46, 204, 113) 
                pdf.set_text_color(0, 0, 0)
            elif val_num < 95:
                pdf.set_fill_color(241, 196, 15) 
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.set_fill_color(231, 76, 60) 
                pdf.set_text_color(255, 255, 255)
            pdf.cell(15, 6, v2, border=1, align="C", fill=True)
            pdf.set_fill_color(240, 240, 240); pdf.set_text_color(0, 0, 0)
        else:
            pdf.cell(15, 6, v2, border=1, align="C")
            
        pdf.cell(5, 6, "", border=0)
        pdf.cell(45, 6, n3, border=1)
        if v3 != "":
            if val3 < 3: pdf.set_fill_color(46, 204, 113); pdf.set_text_color(0,0,0)
            elif val3 < 5: pdf.set_fill_color(241, 196, 15); pdf.set_text_color(0,0,0)
            elif val3 < 7.2: pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255,255,255)
            elif val3 < 9: pdf.set_fill_color(231, 76, 60); pdf.set_text_color(255,255,255)
            else: pdf.set_fill_color(142, 0, 0); pdf.set_text_color(255,255,255)
            pdf.cell(15, 6, v3, border=1, align="C", fill=True)
        else:
            pdf.cell(15, 6, v3, border=1, align="C")
        pdf.set_fill_color(240, 240, 240); pdf.set_text_color(0, 0, 0)
        pdf.ln()

    df_plot = df_filtrado.dropna(subset=['M.O'])
    if not df_plot.empty:
        fig_g1 = px.scatter(df_plot, x='M.O', y='Gr.T', title="Matriz Bivariada: Cinética de Crecimiento vs. Tiempo al PHV")
        fig_g1.update_traces(marker=dict(size=16, color='#3498DB', line=dict(width=1, color='white')))
        fig_g1.add_hline(y=7, line_dash="dash", line_color="#E74C3C", line_width=2)
        fig_g1.add_vline(x=0, line_dash="dash", line_color="#E74C3C", line_width=2)
        fig_g1.update_layout(width=960, height=480, title_x=0.5, plot_bgcolor='white', margin=dict(l=60, r=50, t=50, b=60), font=dict(size=16, family='Arial'), xaxis_range=[-3, 3], yaxis_range=[0, 20])
        fig_g1.update_xaxes(showgrid=True, gridcolor='#EFEFEF', title="Tiempo al PHV (Años)")
        fig_g1.update_yaxes(showgrid=True, gridcolor='#EFEFEF', title="Velocidad de Crecimiento (cm/año)")
        
        try:
            img_g1_bytes = safe_render_fig(fig_g1)
            pdf.image(BytesIO(img_g1_bytes), x=10, y=120, w=190)
        except: pass

    # =========================================================
    # PÁGINA 3: MONITOR DE MADURACIÓN
    # =========================================================
    add_page_header("Monitor de Maduración")
    
    pdf.set_y(50)
    df_bar = df_filtrado.dropna(subset=['% PHV']).sort_values('Nombre y Apellido')
    if not df_bar.empty:
        y_max = max(105, df_bar['% PHV'].max() * 1.05)
        colors_b = ['#2ECC71' if val < 85 else ('#F1C40F' if val < 95 else '#E74C3C') for val in df_bar['% PHV']]
        fig_b = px.bar(df_bar, x='Nombre y Apellido', y='% PHV', title="Distribución del Estatus Madurativo (%PAH)", labels={'% PHV': '% PHA'})
        fig_b.update_traces(marker_color=colors_b, texttemplate='%{y:.1f}%', textposition='outside')
        fig_b.add_hline(y=85, line_dash="dash", line_color="#2ECC71", line_width=2, layer="below")
        fig_b.add_hline(y=95, line_dash="dash", line_color="#E74C3C", line_width=2, layer="below")
        fig_b.update_layout(width=960, height=400, title_x=0.5, plot_bgcolor='white', yaxis_range=[60, y_max], margin=dict(l=60, r=50, t=50, b=80), font=dict(size=16, family='Arial'))
        fig_b.update_yaxes(title_text="% PHA")
        
        try:
            img_b_bytes = safe_render_fig(fig_b)
            pdf.image(BytesIO(img_b_bytes), x=10, y=50, w=190)
        except: pass

    if not df_plot.empty:
        fig_c = px.scatter(df_plot, x='M.O', y='Gr.T', title=f"Ubicación de {jug_sel} en el Plantel")
        fig_c.update_traces(marker=dict(size=14, color='#95A5A6', line=dict(width=1, color='white')))
        fig_c.add_hline(y=7, line_dash="dash", line_color="#E74C3C", line_width=2)
        fig_c.add_vline(x=0, line_dash="dash", line_color="#E74C3C", line_width=2)
        if not data_jug.empty:
            fig_c.add_scatter(x=data_jug['M.O'], y=data_jug['Gr.T'], mode='markers', marker=dict(size=24, color='#F1C40F', symbol='star', line=dict(width=2, color='black')), name=jug_sel)
        fig_c.update_layout(width=960, height=480, title_x=0.5, plot_bgcolor='white', xaxis_range=[-3, 3], yaxis_range=[0, 20], margin=dict(l=60, r=50, t=50, b=60), font=dict(size=16, family='Arial'))
        fig_c.update_xaxes(showgrid=True, gridcolor='#EFEFEF', title="Tiempo al PHV (Años)")
        fig_c.update_yaxes(showgrid=True, gridcolor='#EFEFEF', title="Velocidad de Crecimiento (cm/año)")
        
        try:
            img_c_bytes = safe_render_fig(fig_c)
            pdf.image(BytesIO(img_c_bytes), x=10, y=145, w=190)
        except Exception as e:
            pdf.set_xy(10, 160)
            pdf.set_font("Arial", "B", 10)
            pdf.set_text_color(255, 0, 0)
            pdf.multi_cell(190, 8, f"Error Render Gráfico 4: {str(e)}", align="C")

    return bytes(pdf.output())
