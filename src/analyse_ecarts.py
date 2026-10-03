"""
Analyse des écarts budgétaires — SQL + Python (VERSION CORRIGÉE)
Contexte : contrôle de gestion PME gabonaise
"""
import sqlite3
import pandas as pd
from pathlib import Path


class AnalyseEcarts:
    """Analyseur d'écarts budgétaires"""
    
    def __init__(self, db_path='database/controle_gestion.db'):
        self.conn = sqlite3.connect(db_path)
    
    def query(self, sql):
        return pd.read_sql_query(sql, self.conn)
    
    # ==============================================================
    # REQUÊTE 1 : ÉCARTS PAR DÉPARTEMENT (corrigée)
    # ==============================================================
    def ecarts_par_departement(self):
        return self.query("""
            WITH budget_agg AS (
                SELECT departement, SUM(budget_annuel_fcfa) AS budget_total
                FROM budget
                GROUP BY departement
            ),
            depense_agg AS (
                SELECT departement, SUM(depense_reelle_fcfa) AS depense_totale
                FROM depenses
                GROUP BY departement
            )
            SELECT 
                b.departement,
                ROUND(b.budget_total, 0) AS budget_total,
                ROUND(d.depense_totale, 0) AS depense_totale,
                ROUND(d.depense_totale - b.budget_total, 0) AS ecart_fcfa,
                ROUND(100.0 * (d.depense_totale - b.budget_total) / b.budget_total, 2) AS ecart_pct,
                CASE 
                    WHEN d.depense_totale > b.budget_total THEN '🔴 Dépassement'
                    ELSE '🟢 Économie'
                END AS statut
            FROM budget_agg b
            LEFT JOIN depense_agg d ON b.departement = d.departement
            ORDER BY ecart_pct DESC
        """)
    
    # ==============================================================
    # REQUÊTE 2 : ÉCARTS PAR POSTE (corrigée)
    # ==============================================================
    def ecarts_par_poste(self):
        return self.query("""
            WITH budget_agg AS (
                SELECT departement, poste, compte_syscohada, 
                       SUM(budget_annuel_fcfa) AS budget_total
                FROM budget
                GROUP BY departement, poste, compte_syscohada
            ),
            depense_agg AS (
                SELECT departement, poste, 
                       SUM(depense_reelle_fcfa) AS depense_totale
                FROM depenses
                GROUP BY departement, poste
            )
            SELECT 
                b.departement,
                b.poste,
                b.compte_syscohada,
                ROUND(b.budget_total, 0) AS budget_total,
                ROUND(d.depense_totale, 0) AS depense_totale,
                ROUND(d.depense_totale - b.budget_total, 0) AS ecart_fcfa,
                ROUND(100.0 * (d.depense_totale - b.budget_total) / b.budget_total, 2) AS ecart_pct
            FROM budget_agg b
            LEFT JOIN depense_agg d 
                ON b.departement = d.departement 
                AND b.poste = d.poste
            ORDER BY ecart_pct DESC
        """)
    
    # ==============================================================
    # REQUÊTE 3 : ÉCARTS MENSUELS
    # ==============================================================
    def ecarts_mensuels(self):
        return self.query("""
            SELECT 
                mois,
                ROUND(SUM(budget_mensuel_fcfa), 0) AS budget_mois,
                ROUND(SUM(depense_reelle_fcfa), 0) AS depense_mois,
                ROUND(SUM(depense_reelle_fcfa) - SUM(budget_mensuel_fcfa), 0) AS ecart_fcfa,
                ROUND(100.0 * (SUM(depense_reelle_fcfa) - SUM(budget_mensuel_fcfa)) 
                      / SUM(budget_mensuel_fcfa), 2) AS ecart_pct
            FROM depenses
            GROUP BY mois
            ORDER BY mois
        """)
    
    # ==============================================================
    # REQUÊTE 4 : TOP 10 DÉPASSEMENTS (corrigée)
    # ==============================================================
    def top_depassements(self, limite=10):
        return self.query(f"""
            WITH budget_agg AS (
                SELECT departement, poste, 
                       SUM(budget_annuel_fcfa) AS budget_total
                FROM budget
                GROUP BY departement, poste
            ),
            depense_agg AS (
                SELECT departement, poste, 
                       SUM(depense_reelle_fcfa) AS depense_totale
                FROM depenses
                GROUP BY departement, poste
            )
            SELECT 
                b.departement,
                b.poste,
                ROUND(b.budget_total, 0) AS budget_total,
                ROUND(d.depense_totale, 0) AS depense_totale,
                ROUND(d.depense_totale - b.budget_total, 0) AS ecart_fcfa,
                ROUND(100.0 * (d.depense_totale - b.budget_total) / b.budget_total, 2) AS ecart_pct
            FROM budget_agg b
            JOIN depense_agg d 
                ON b.departement = d.departement 
                AND b.poste = d.poste
            WHERE d.depense_totale > b.budget_total
            ORDER BY ecart_fcfa DESC
            LIMIT {limite}
        """)
    
    # ==============================================================
    # REQUÊTE 5 : ANALYSE PAR COMPTE SYSCOHADA (corrigée)
    # ==============================================================
    def analyse_par_compte(self):
        return self.query("""
            WITH budget_agg AS (
                SELECT compte_syscohada, 
                       COUNT(DISTINCT departement || poste) AS nb_postes,
                       SUM(budget_annuel_fcfa) AS budget_total
                FROM budget
                GROUP BY compte_syscohada
            ),
            depense_agg AS (
                SELECT compte_syscohada, 
                       SUM(depense_reelle_fcfa) AS depense_totale
                FROM depenses
                GROUP BY compte_syscohada
            )
            SELECT 
                b.compte_syscohada,
                b.nb_postes,
                ROUND(b.budget_total, 0) AS budget_total,
                ROUND(d.depense_totale, 0) AS depense_totale,
                ROUND(100.0 * (d.depense_totale - b.budget_total) / b.budget_total, 2) AS ecart_pct
            FROM budget_agg b
            LEFT JOIN depense_agg d ON b.compte_syscohada = d.compte_syscohada
            ORDER BY d.depense_totale DESC
        """)
    
    # ==============================================================
    # REQUÊTE 6 : DÉRIVE PAR DÉPARTEMENT × MOIS
    # ==============================================================
    def derive_dept_mois(self):
        return self.query("""
            SELECT 
                departement,
                mois,
                ROUND(SUM(depense_reelle_fcfa), 0) AS depense,
                ROUND(SUM(budget_mensuel_fcfa), 0) AS budget,
                ROUND(100.0 * (SUM(depense_reelle_fcfa) - SUM(budget_mensuel_fcfa)) 
                      / SUM(budget_mensuel_fcfa), 2) AS ecart_pct
            FROM depenses
            GROUP BY departement, mois
            ORDER BY departement, mois
        """)
    
    # ==============================================================
    # REQUÊTE 7 : KPI CONTRÔLE DE GESTION (corrigée)
    # ==============================================================
    def kpi_cg(self):
        return self.query("""
            WITH budget_total AS (
                SELECT SUM(budget_annuel_fcfa) AS b FROM budget
            ),
            depense_total AS (
                SELECT SUM(depense_reelle_fcfa) AS d FROM depenses
            )
            SELECT 
                ROUND(b, 0) AS budget_total,
                ROUND(d, 0) AS depense_totale,
                ROUND(d - b, 0) AS ecart_global,
                ROUND(100.0 * (d - b) / b, 2) AS ecart_pct,
                ROUND(100.0 * d / b, 2) AS taux_consommation_pct
            FROM budget_total, depense_total
        """)
    
    def close(self):
        self.conn.close()


# =====================================================================
# AFFICHAGE
# =====================================================================
def afficher_tableau(df, titre, pct_cols=None, fcfa_cols=None):
    """Affiche un DataFrame formaté"""
    print(f"\n{titre}")
    print("─" * 75)
    
    if len(df) == 0:
        print("   ⚠️  Aucune donnée")
        return
    
    df_display = df.copy()
    
    if fcfa_cols:
        for col in fcfa_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(
                    lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A"
                )
    
    if pct_cols:
        for col in pct_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(
                    lambda x: f"{x:+.2f} %" if pd.notna(x) else "N/A"
                )
    
    print(df_display.to_string(index=False))


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("=" * 75)
    print("📊 ANALYSE DES ÉCARTS BUDGÉTAIRES")
    print("=" * 75)
    
    analyse = AnalyseEcarts()
    
    # ---- KPI globaux ----
    print("\n" + "=" * 75)
    print("🎯 KPI DE CONTRÔLE DE GESTION")
    print("=" * 75)
    kpi = analyse.kpi_cg().iloc[0]
    print(f"\n   • Budget total           : {kpi['budget_total']:>15,.0f} FCFA")
    print(f"   • Dépenses totales       : {kpi['depense_totale']:>15,.0f} FCFA")
    print(f"   • Écart global           : {kpi['ecart_global']:>+15,.0f} FCFA")
    print(f"   • Écart %                : {kpi['ecart_pct']:>+15.2f} %")
    print(f"   • Taux de consommation   : {kpi['taux_consommation_pct']:>15.2f} %")
    
    # ---- Écarts par département ----
    df_dept = analyse.ecarts_par_departement()
    afficher_tableau(
        df_dept,
        "🏢 ÉCARTS PAR DÉPARTEMENT",
        pct_cols=['ecart_pct'],
        fcfa_cols=['budget_total', 'depense_totale', 'ecart_fcfa']
    )
    
    # ---- Top dépassements ----
    df_top = analyse.top_depassements(10)
    afficher_tableau(
        df_top,
        "🚨 TOP 10 POSTES EN DÉPASSEMENT",
        pct_cols=['ecart_pct'],
        fcfa_cols=['budget_total', 'depense_totale', 'ecart_fcfa']
    )
    
    # ---- Analyse par compte SYSCOHADA ----
    df_compte = analyse.analyse_par_compte()
    afficher_tableau(
        df_compte,
        "📋 ANALYSE PAR COMPTE SYSCOHADA",
        pct_cols=['ecart_pct'],
        fcfa_cols=['budget_total', 'depense_totale']
    )
    
    # ---- Écarts mensuels ----
    df_mois = analyse.ecarts_mensuels()
    afficher_tableau(
        df_mois,
        "📅 ÉCARTS MENSUELS",
        pct_cols=['ecart_pct'],
        fcfa_cols=['budget_mois', 'depense_mois', 'ecart_fcfa']
    )
    
    # ---- Sauvegarde CSV ----
    print("\n" + "=" * 75)
    print("💾 SAUVEGARDE DES ANALYSES")
    print("=" * 75)
    Path('reports/sql').mkdir(parents=True, exist_ok=True)
    
    df_dept.to_csv('reports/sql/ecarts_par_departement.csv', index=False)
    df_top.to_csv('reports/sql/top_depassements.csv', index=False)
    df_compte.to_csv('reports/sql/analyse_par_compte.csv', index=False)
    df_mois.to_csv('reports/sql/ecarts_mensuels.csv', index=False)
    
    print("   ✅ ecarts_par_departement.csv")
    print("   ✅ top_depassements.csv")
    print("   ✅ analyse_par_compte.csv")
    print("   ✅ ecarts_mensuels.csv")
    
    analyse.close()
    
    print("\n" + "=" * 75)
    print("✅ ANALYSE DES ÉCARTS TERMINÉE")
    print("=" * 75)