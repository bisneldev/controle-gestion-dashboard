"""
Génération automatique du rapport de contrôle de gestion
- Rapport PDF pour la Direction
- Fichier Excel multi-onglets
"""
import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path
from datetime import datetime

# PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# Excel
import xlsxwriter


# =====================================================================
# CHARGEMENT
# =====================================================================
def charger_donnees(db_path='database/controle_gestion.db'):
    conn = sqlite3.connect(db_path)
    df_budget = pd.read_sql_query("SELECT * FROM budget", conn)
    df_depenses = pd.read_sql_query("SELECT * FROM depenses", conn)
    df_clients = pd.read_sql_query("SELECT * FROM factures_clients", conn)
    df_fournisseurs = pd.read_sql_query("SELECT * FROM factures_fournisseurs", conn)
    conn.close()
    return df_budget, df_depenses, df_clients, df_fournisseurs


# =====================================================================
# KPI
# =====================================================================
def calculer_kpis(df_budget, df_depenses, df_clients, df_fournisseurs):
    total_budget = df_budget['budget_annuel_fcfa'].sum()
    total_depense = df_depenses['depense_reelle_fcfa'].sum()
    ca_total = df_clients['montant_fcfa'].sum()
    ca_encaisse = df_clients[df_clients['statut'] == 'Payée']['montant_fcfa'].sum()
    ca_retard = df_clients[df_clients['statut'] == 'En retard']['montant_fcfa'].sum()
    ca_impaye = df_clients[df_clients['statut'] == 'Impayée']['montant_fcfa'].sum()
    dso = df_clients[df_clients['delai_jours'].notna()]['delai_jours'].mean()
    dpo = df_fournisseurs['delai_jours'].mean()
    dettes = df_fournisseurs[df_fournisseurs['statut'] == 'À payer']['montant_fcfa'].sum()
    bfr = (ca_retard + ca_impaye) - dettes
    
    return {
        'total_budget': total_budget,
        'total_depense': total_depense,
        'ecart_global': total_depense - total_budget,
        'ecart_pct': (total_depense - total_budget) / total_budget * 100,
        'ca_total': ca_total,
        'ca_encaisse': ca_encaisse,
        'ca_retard': ca_retard,
        'ca_impaye': ca_impaye,
        'taux_recouvrement': ca_encaisse / ca_total * 100,
        'dso': dso,
        'dpo': dpo,
        'bfr': bfr,
    }


# =====================================================================
# RAPPORT PDF
# =====================================================================
def generer_pdf(kpis, df_dept, df_mois, df_lents, output='reports/rapport_cg.pdf'):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    print(f"📄 Génération du rapport PDF...")
    
    doc = SimpleDocTemplate(output, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    titre_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=20, textColor=colors.HexColor('#1f3a5f'),
        spaceAfter=6, alignment=TA_CENTER
    )
    h1 = ParagraphStyle('H1', parent=styles['Heading1'],
                        fontSize=14, textColor=colors.HexColor('#1f3a5f'),
                        spaceBefore=20, spaceAfter=10)
    normal = ParagraphStyle('N', parent=styles['Normal'],
                            fontSize=10, alignment=TA_JUSTIFY, leading=14)
    small = ParagraphStyle('S', parent=styles['Normal'],
                           fontSize=8, textColor=colors.grey)
    
    elements = []
    
    # ---- EN-TÊTE ----
    elements.append(Paragraph("RAPPORT DE CONTRÔLE DE GESTION", titre_style))
    elements.append(Paragraph(
        "Exercice 2025 — PME Gabon",
        ParagraphStyle('sub', parent=styles['Normal'], fontSize=11,
                       textColor=colors.HexColor('#666'), alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        ParagraphStyle('d', parent=small, alignment=TA_CENTER)
    ))
    elements.append(Spacer(1, 20))
    
    # ---- SECTION 1 : SYNTHÈSE ----
    elements.append(Paragraph("1. Synthèse exécutive", h1))
    synthesis = f"""
    L'exercice 2025 se caractérise par un <b>dépassement budgétaire global de 
    {kpis['ecart_global']/1e6:+.1f} M FCFA ({kpis['ecart_pct']:+.2f} %)</b>. 
    Le chiffre d'affaires s'élève à <b>{kpis['ca_total']/1e6:.1f} M FCFA</b>, 
    avec un taux de recouvrement de <b>{kpis['taux_recouvrement']:.1f} %</b>. 
    Le DSO de <b>{kpis['dso']:.1f} jours</b> et le BFR de 
    <b>{kpis['bfr']/1e6:+.1f} M FCFA</b> appellent une vigilance particulière 
    sur la trésorerie.
    """
    elements.append(Paragraph(synthesis, normal))
    elements.append(Spacer(1, 15))
    
    # ---- TABLEAU KPI ----
    data_kpi = [
        ['Indicateur', 'Valeur'],
        ['Budget total', f"{kpis['total_budget']/1e6:.1f} M FCFA"],
        ['Dépenses réelles', f"{kpis['total_depense']/1e6:.1f} M FCFA"],
        ['Écart global', f"{kpis['ecart_global']/1e6:+.1f} M FCFA ({kpis['ecart_pct']:+.2f} %)"],
        ['Chiffre d\'affaires', f"{kpis['ca_total']/1e6:.1f} M FCFA"],
        ['Taux de recouvrement', f"{kpis['taux_recouvrement']:.2f} %"],
        ['DSO', f"{kpis['dso']:.1f} jours"],
        ['DPO', f"{kpis['dpo']:.1f} jours"],
        ['BFR', f"{kpis['bfr']/1e6:+.1f} M FCFA"],
    ]
    
    table = Table(data_kpi, colWidths=[9*cm, 7*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    
    # ---- SECTION 2 : ÉCARTS PAR DÉPARTEMENT ----
    elements.append(Paragraph("2. Écarts budgétaires par département", h1))
    
    data_dept = [['Département', 'Budget (M)', 'Dépenses (M)', 'Écart (M)', 'Écart %']]
    for _, row in df_dept.iterrows():
        data_dept.append([
            row['departement'],
            f"{row['budget']/1e6:.1f}",
            f"{row['depense']/1e6:.1f}",
            f"{row['ecart']/1e6:+.1f}",
            f"{row['ecart_pct']:+.2f} %",
        ])
    
    t2 = Table(data_dept, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t2)
    
    elements.append(Spacer(1, 10))
    worst = df_dept.iloc[0]
    elements.append(Paragraph(
        f"<b>Constat :</b> le département <b>{worst['departement']}</b> présente "
        f"le dépassement le plus important (<b>{worst['ecart_pct']:+.2f} %</b>), "
        f"soit {worst['ecart']/1e6:+.1f} M FCFA.",
        normal
    ))
    
    # ---- PAGE BREAK ----
    elements.append(PageBreak())
    
    # ---- SECTION 3 : CLIENTS LENTS ----
    elements.append(Paragraph("3. Créances clients — Top 10 clients lents", h1))
    
    data_clients = [['Client', 'Nb factures', 'Délai moyen (j)', 'Taux impayés (%)']]
    for _, row in df_lents.head(10).iterrows():
        data_clients.append([
            row['client'],
            f"{int(row['nb'])}",
            f"{row['delai']:.1f}",
            f"{row['taux_impayes']:.1f}",
        ])
    
    t3 = Table(data_clients, colWidths=[6*cm, 3*cm, 3*cm, 4*cm])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t3)
    
    # ---- SECTION 4 : ÉCARTS MENSUELS ----
    elements.append(Paragraph("4. Écarts budgétaires mensuels", h1))
    
    data_mois = [['Mois', 'Budget (M)', 'Dépenses (M)', 'Écart %']]
    for _, row in df_mois.iterrows():
        data_mois.append([
            row['mois'],
            f"{row['budget']/1e6:.1f}",
            f"{row['depense']/1e6:.1f}",
            f"{row['ecart_pct']:+.2f} %",
        ])
    
    t4 = Table(data_mois, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(t4)
    
    # ---- SECTION 5 : RECOMMANDATIONS ----
    elements.append(Paragraph("5. Recommandations", h1))
    
    recos = [
        f"<b>Maîtriser les dérives budgétaires</b> sur IT (+17 %) et "
        f"Production (+8 %) — audit des postes 'Salaires' et 'Matières premières'.",
        
        f"<b>Optimiser le recouvrement client</b> : le DSO de {kpis['dso']:.1f} jours "
        f"génère un BFR positif de {kpis['bfr']/1e6:+.1f} M FCFA à financer.",
        
        f"<b>Cibler 5 clients prioritaires</b> pour relance : TOTAL Gabon, "
        f"Groupe CFAO, BGFI Business, Perenco, CDC Gabon.",
        
        f"<b>Réduire les impayés</b> (7,6 % du CA, soit "
        f"{kpis['ca_impaye']/1e6:.1f} M FCFA) via renforcement des conditions "
        f"de crédit ou garanties.",
        
        f"<b>Anticiper les tensions de trésorerie</b> aux mois de janvier et décembre "
        f"qui concentrent les principaux dépassements.",
    ]
    
    for i, reco in enumerate(recos, 1):
        elements.append(Paragraph(f"{i}. {reco}", normal))
        elements.append(Spacer(1, 6))
    
    # ---- FOOTER ----
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "Document généré automatiquement — Système de Contrôle de Gestion",
        small
    ))
    
    doc.build(elements)
    print(f"✅ Rapport PDF généré : {output}")
    return output


# =====================================================================
# RAPPORT EXCEL
# =====================================================================
def generer_excel(kpis, df_dept, df_mois, df_lents, df_compte, 
                  output='reports/rapport_cg.xlsx'):
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    print(f"📊 Génération du rapport Excel...")
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        titre_fmt = workbook.add_format({
            'bold': True, 'font_size': 16,
            'font_color': '#1f3a5f', 'align': 'center'
        })
        
        # ---- Onglet Synthèse ----
        df_kpi = pd.DataFrame([
            ['Budget total (FCFA)', kpis['total_budget']],
            ['Dépenses réelles (FCFA)', kpis['total_depense']],
            ['Écart global (FCFA)', kpis['ecart_global']],
            ['Écart (%)', round(kpis['ecart_pct'], 2)],
            ['Chiffre d\'affaires (FCFA)', kpis['ca_total']],
            ['Taux de recouvrement (%)', round(kpis['taux_recouvrement'], 2)],
            ['DSO (jours)', round(kpis['dso'], 1)],
            ['DPO (jours)', round(kpis['dpo'], 1)],
            ['BFR (FCFA)', kpis['bfr']],
        ], columns=['Indicateur', 'Valeur'])
        
        df_kpi.to_excel(writer, sheet_name='Synthèse', index=False, startrow=2)
        ws = writer.sheets['Synthèse']
        ws.write('A1', 'RAPPORT DE CONTRÔLE DE GESTION — 2025', titre_fmt)
        ws.set_column('A:A', 35)
        ws.set_column('B:B', 25)
        
        # ---- Onglet Départements ----
        df_dept.to_excel(writer, sheet_name='Départements', index=False)
        ws = writer.sheets['Départements']
        ws.set_column('A:F', 20)
        
        # ---- Onglet Clients lents ----
        df_lents.to_excel(writer, sheet_name='Clients lents', index=False)
        ws = writer.sheets['Clients lents']
        ws.set_column('A:D', 22)
        
        # ---- Onglet Mensuel ----
        df_mois.to_excel(writer, sheet_name='Mensuel', index=False)
        ws = writer.sheets['Mensuel']
        ws.set_column('A:D', 18)
        
        # ---- Onglet Comptes SYSCOHADA ----
        df_compte.to_excel(writer, sheet_name='SYSCOHADA', index=False)
        ws = writer.sheets['SYSCOHADA']
        ws.set_column('A:E', 18)
    
    print(f"✅ Rapport Excel généré : {output}")
    return output


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("=" * 75)
    print("📄 GÉNÉRATION DES RAPPORTS DE CONTRÔLE DE GESTION")
    print("=" * 75)
    
    print("\n🔄 Chargement des données...")
    df_budget, df_depenses, df_clients, df_fournisseurs = charger_donnees()
    print(f"✅ {len(df_budget)+len(df_depenses)+len(df_clients)+len(df_fournisseurs)} lignes")
    
    # KPIs
    kpis = calculer_kpis(df_budget, df_depenses, df_clients, df_fournisseurs)
    
    # Préparer les DataFrames pour le rapport
    budget_agg = df_budget.groupby('departement')['budget_annuel_fcfa'].sum()
    depense_agg = df_depenses.groupby('departement')['depense_reelle_fcfa'].sum()
    df_dept = pd.DataFrame({
        'departement': budget_agg.index,
        'budget': budget_agg.values,
        'depense': depense_agg.values,
    })
    df_dept['ecart'] = df_dept['depense'] - df_dept['budget']
    df_dept['ecart_pct'] = (df_dept['ecart'] / df_dept['budget'] * 100).round(2)
    df_dept = df_dept.sort_values('ecart_pct', ascending=False)
    
    df_mois = df_depenses.groupby('mois').agg(
        budget=('budget_mensuel_fcfa', 'sum'),
        depense=('depense_reelle_fcfa', 'sum')
    ).reset_index()
    df_mois['ecart_pct'] = ((df_mois['depense'] - df_mois['budget']) / df_mois['budget'] * 100).round(2)
    
    df_lents = df_clients[df_clients['delai_jours'].notna()].groupby('client').agg(
        nb=('facture_id', 'count'),
        delai=('delai_jours', 'mean'),
        taux_impayes=('statut', lambda x: (x == 'Impayée').sum() / len(x) * 100)
    ).reset_index()
    df_lents = df_lents[df_lents['nb'] >= 5].sort_values('delai', ascending=False).round(2)
    
    # Analyse par compte SYSCOHADA
    b_agg = df_budget.groupby('compte_syscohada')['budget_annuel_fcfa'].sum().reset_index()
    d_agg = df_depenses.groupby('compte_syscohada')['depense_reelle_fcfa'].sum().reset_index()
    df_compte = b_agg.merge(d_agg, on='compte_syscohada')
    df_compte['ecart_pct'] = ((df_compte['depense_reelle_fcfa'] - df_compte['budget_annuel_fcfa']) 
                              / df_compte['budget_annuel_fcfa'] * 100).round(2)
    
    # Génération
    print()
    pdf_path = generer_pdf(kpis, df_dept, df_mois, df_lents)
    print()
    excel_path = generer_excel(kpis, df_dept, df_mois, df_lents, df_compte)
    
    print("\n" + "=" * 75)
    print("✅ RAPPORTS GÉNÉRÉS")
    print("=" * 75)
    print(f"📄 PDF   : {pdf_path}")
    print(f"📊 Excel : {excel_path}")