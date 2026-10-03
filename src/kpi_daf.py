"""
Calcul des KPI DAF (Direction Administrative et Financière)
Contexte : contrôle de gestion PME gabonaise
"""
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


class KPIDAF:
    """Calcul des indicateurs financiers clés"""
    
    def __init__(self, db_path='database/controle_gestion.db'):
        self.conn = sqlite3.connect(db_path)
    
    def query(self, sql):
        return pd.read_sql_query(sql, self.conn)
    
    # ==============================================================
    # 1. DSO — Days Sales Outstanding
    # ==============================================================
    def calculer_dso(self):
        """
        DSO = Délai moyen d'encaissement des créances clients.
        Formule simplifiée : moyenne des délais d'encaissement des factures payées.
        """
        df = self.query("""
            SELECT 
                COUNT(*) AS nb_factures_total,
                SUM(CASE WHEN statut = 'Payée' THEN 1 ELSE 0 END) AS nb_payees,
                SUM(CASE WHEN statut = 'Payée' THEN montant_fcfa ELSE 0 END) AS ca_encaisse,
                SUM(montant_fcfa) AS ca_total,
                AVG(CASE WHEN statut = 'Payée' THEN delai_jours END) AS dso_moyen,
                AVG(CASE WHEN statut IN ('En retard', 'Impayée') THEN delai_jours END) AS delai_retard
            FROM factures_clients
        """)
        return df.iloc[0].to_dict()
    
    def dso_par_client(self):
        """DSO détaillé par client (pour identifier les mauvais payeurs)"""
        return self.query("""
            SELECT 
                client,
                COUNT(*) AS nb_factures,
                ROUND(SUM(montant_fcfa), 0) AS ca_total,
                ROUND(AVG(CASE WHEN delai_jours IS NOT NULL THEN delai_jours END), 1) AS delai_moyen,
                SUM(CASE WHEN statut = 'Impayée' THEN 1 ELSE 0 END) AS nb_impayees,
                ROUND(100.0 * SUM(CASE WHEN statut = 'Impayée' THEN 1 ELSE 0 END) 
                      / COUNT(*), 2) AS taux_impayes_pct
            FROM factures_clients
            GROUP BY client
            HAVING COUNT(*) >= 5
            ORDER BY delai_moyen DESC
        """)
    
    # ==============================================================
    # 2. DPO — Days Payable Outstanding
    # ==============================================================
    def calculer_dpo(self):
        """
        DPO = Délai moyen de paiement des fournisseurs.
        """
        df = self.query("""
            SELECT 
                COUNT(*) AS nb_factures_total,
                SUM(montant_fcfa) AS achats_total,
                AVG(delai_jours) AS dpo_moyen,
                MIN(delai_jours) AS dpo_min,
                MAX(delai_jours) AS dpo_max,
                SUM(CASE WHEN statut = 'À payer' THEN montant_fcfa ELSE 0 END) AS dettes_restantes
            FROM factures_fournisseurs
        """)
        return df.iloc[0].to_dict()
    
    # ==============================================================
    # 3. BFR — Besoin en Fonds de Roulement
    # ==============================================================
    def calculer_bfr(self):
        """
        BFR = Créances clients + Stocks - Dettes fournisseurs
        Version simplifiée : Créances clients - Dettes fournisseurs
        """
        df = self.query("""
            WITH creances AS (
                SELECT 
                    SUM(CASE WHEN statut IN ('En retard', 'Impayée') 
                        THEN montant_fcfa ELSE 0 END) AS creances_clients
                FROM factures_clients
            ),
            dettes AS (
                SELECT 
                    SUM(CASE WHEN statut = 'À payer' 
                        THEN montant_fcfa ELSE 0 END) AS dettes_fournisseurs
                FROM factures_fournisseurs
            )
            SELECT 
                ROUND(creances_clients, 0) AS creances_clients,
                ROUND(dettes_fournisseurs, 0) AS dettes_fournisseurs,
                ROUND(creances_clients - dettes_fournisseurs, 0) AS bfr
            FROM creances, dettes
        """)
        return df.iloc[0].to_dict()
    
    # ==============================================================
    # 4. TAUX DE RECOUVREMENT
    # ==============================================================
    def taux_recouvrement(self):
        """Taux de recouvrement des créances clients"""
        df = self.query("""
            SELECT 
                ROUND(100.0 * SUM(CASE WHEN statut = 'Payée' THEN montant_fcfa ELSE 0 END) 
                      / SUM(montant_fcfa), 2) AS taux_recouvrement_pct,
                ROUND(SUM(CASE WHEN statut = 'Payée' THEN montant_fcfa ELSE 0 END), 0) AS ca_encaisse,
                ROUND(SUM(CASE WHEN statut = 'En retard' THEN montant_fcfa ELSE 0 END), 0) AS ca_en_retard,
                ROUND(SUM(CASE WHEN statut = 'Impayée' THEN montant_fcfa ELSE 0 END), 0) AS ca_impaye,
                ROUND(SUM(montant_fcfa), 0) AS ca_total
            FROM factures_clients
        """)
        return df.iloc[0].to_dict()
    
    # ==============================================================
    # 5. CRÉANCES DOUTEUSES
    # ==============================================================
    def creances_douteuses(self):
        """Analyse des créances à risque"""
        return self.query("""
            SELECT 
                statut,
                COUNT(*) AS nb_factures,
                ROUND(SUM(montant_fcfa), 0) AS montant_fcfa,
                ROUND(100.0 * SUM(montant_fcfa) / (SELECT SUM(montant_fcfa) FROM factures_clients), 2) AS pct_ca,
                ROUND(AVG(delai_jours), 1) AS delai_moyen
            FROM factures_clients
            GROUP BY statut
            ORDER BY montant_fcfa DESC
        """)
    
    # ==============================================================
    # 6. SYNTHÈSE DIRECTION — Tableau de bord DAF
    # ==============================================================
    def synthese_daf(self):
        """Synthèse des indicateurs pour la Direction"""
        dso = self.calculer_dso()
        dpo = self.calculer_dpo()
        bfr = self.calculer_bfr()
        recouv = self.taux_recouvrement()
        
        indicateurs = []
        
        # CA
        indicateurs.append({
            'indicateur': '💰 Chiffre d\'affaires annuel',
            'valeur': f"{recouv['ca_total']/1e6:.1f} M FCFA",
            'statut': '✅'
        })
        
        # CA encaissé
        indicateurs.append({
            'indicateur': '✅ CA encaissé',
            'valeur': f"{recouv['ca_encaisse']/1e6:.1f} M FCFA ({recouv['taux_recouvrement_pct']:.1f} %)",
            'statut': '🟢' if recouv['taux_recouvrement_pct'] > 70 else '⚠️'
        })
        
        # DSO
        dso_val = dso['dso_moyen']
        indicateurs.append({
            'indicateur': '📅 DSO (délai encaissement client)',
            'valeur': f"{dso_val:.1f} jours",
            'statut': '🟢' if dso_val < 45 else '⚠️' if dso_val < 60 else '🔴'
        })
        
        # DPO
        dpo_val = dpo['dpo_moyen']
        indicateurs.append({
            'indicateur': '📅 DPO (délai paiement fournisseur)',
            'valeur': f"{dpo_val:.1f} jours",
            'statut': '🟢' if dpo_val > 45 else '⚠️'
        })
        
        # BFR
        indicateurs.append({
            'indicateur': '📊 BFR',
            'valeur': f"{bfr['bfr']/1e6:+.1f} M FCFA",
            'statut': '🟢' if bfr['bfr'] < 0 else '⚠️'
        })
        
        # Créances clients
        indicateurs.append({
            'indicateur': '⚠️ Créances clients en risque',
            'valeur': f"{bfr['creances_clients']/1e6:.1f} M FCFA",
            'statut': '🔴' if bfr['creances_clients'] > recouv['ca_total'] * 0.15 else '⚠️'
        })
        
        # Dettes fournisseurs
        indicateurs.append({
            'indicateur': '💳 Dettes fournisseurs',
            'valeur': f"{bfr['dettes_fournisseurs']/1e6:.1f} M FCFA",
            'statut': '✅'
        })
        
        return pd.DataFrame(indicateurs)
    
    def close(self):
        self.conn.close()


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("=" * 75)
    print("📊 KPI DAF — INDICATEURS FINANCIERS CLÉS")
    print("=" * 75)
    
    kpi = KPIDAF()
    
    # ---- 1. DSO ----
    dso = kpi.calculer_dso()
    print(f"\n{'─' * 75}")
    print("1️⃣ DSO — Days Sales Outstanding (Délai d'encaissement client)")
    print(f"{'─' * 75}")
    print(f"   • Nombre total de factures     : {dso['nb_factures_total']:,}")
    print(f"   • Factures payées              : {int(dso['nb_payees']):,} "
          f"({dso['nb_payees']/dso['nb_factures_total']*100:.1f} %)")
    print(f"   • CA total                     : {dso['ca_total']:>15,.0f} FCFA")
    print(f"   • CA encaissé                  : {dso['ca_encaisse']:>15,.0f} FCFA")
    print(f"   • DSO moyen                    : {dso['dso_moyen']:>15.1f} jours")
    print(f"   • Délai moyen en retard        : {dso['delai_retard']:>15.1f} jours")
    
    # ---- Top clients lents ----
    print(f"\n   🐢 Top 5 clients avec les délais les plus longs :")
    df_lents = kpi.dso_par_client().head(5)
    if len(df_lents) > 0:
        for _, row in df_lents.iterrows():
            print(f"      • {row['client']:25s} : {row['delai_moyen']:>5.1f} jours "
                  f"({row['nb_factures']} factures, taux impayés {row['taux_impayes_pct']:.1f} %)")
    
    # ---- 2. DPO ----
    dpo = kpi.calculer_dpo()
    print(f"\n{'─' * 75}")
    print("2️⃣ DPO — Days Payable Outstanding (Délai de paiement fournisseur)")
    print(f"{'─' * 75}")
    print(f"   • Nombre de factures           : {dpo['nb_factures_total']:,}")
    print(f"   • Achats total                 : {dpo['achats_total']:>15,.0f} FCFA")
    print(f"   • DPO moyen                    : {dpo['dpo_moyen']:>15.1f} jours")
    print(f"   • DPO min / max                : {dpo['dpo_min']:.0f} / {dpo['dpo_max']:.0f} jours")
    print(f"   • Dettes restantes             : {dpo['dettes_restantes']:>15,.0f} FCFA")
    
    # ---- 3. BFR ----
    bfr = kpi.calculer_bfr()
    print(f"\n{'─' * 75}")
    print("3️⃣ BFR — Besoin en Fonds de Roulement")
    print(f"{'─' * 75}")
    print(f"   • Créances clients             : {bfr['creances_clients']:>15,.0f} FCFA")
    print(f"   • Dettes fournisseurs          : {bfr['dettes_fournisseurs']:>15,.0f} FCFA")
    print(f"   • BFR                          : {bfr['bfr']:>+15,.0f} FCFA")
    if bfr['bfr'] > 0:
        print(f"   ⚠️  Interprétation : BFR positif → l'entreprise doit financer son cycle")
    else:
        print(f"   ✅ Interprétation : BFR négatif → les fournisseurs financent l'activité")
    
    # ---- 4. Taux de recouvrement ----
    recouv = kpi.taux_recouvrement()
    print(f"\n{'─' * 75}")
    print("4️⃣ TAUX DE RECOUVREMENT DES CRÉANCES")
    print(f"{'─' * 75}")
    print(f"   • Taux de recouvrement         : {recouv['taux_recouvrement_pct']:>15.2f} %")
    print(f"   • CA encaissé                  : {recouv['ca_encaisse']:>15,.0f} FCFA")
    print(f"   • CA en retard                 : {recouv['ca_en_retard']:>15,.0f} FCFA")
    print(f"   • CA impayé                    : {recouv['ca_impaye']:>15,.0f} FCFA")
    print(f"   • CA total                     : {recouv['ca_total']:>15,.0f} FCFA")
    
    # ---- 5. Créances douteuses ----
    print(f"\n{'─' * 75}")
    print("5️⃣ CRÉANCES DOUTEUSES")
    print(f"{'─' * 75}")
    df_cr = kpi.creances_douteuses()
    for _, row in df_cr.iterrows():
        print(f"   • {row['statut']:12s} : {row['nb_factures']:>3} factures | "
              f"{row['montant_fcfa']:>15,.0f} FCFA ({row['pct_ca']:>5.2f} %)")
    
    # ---- 6. SYNTHÈSE ----
    print(f"\n{'═' * 75}")
    print("🎯 SYNTHÈSE DAF — TABLEAU DE BORD DIRECTION")
    print(f"{'═' * 75}\n")
    synthese = kpi.synthese_daf()
    for _, row in synthese.iterrows():
        print(f"   {row['statut']}  {row['indicateur']:45s} {row['valeur']:>20s}")
    
    # ---- Sauvegarde ----
    print(f"\n{'─' * 75}")
    print("💾 SAUVEGARDE DES KPI")
    print(f"{'─' * 75}")
    Path('reports/kpi').mkdir(parents=True, exist_ok=True)
    
    synthese.to_csv('reports/kpi/synthese_daf.csv', index=False)
    kpi.dso_par_client().to_csv('reports/kpi/dso_par_client.csv', index=False)
    kpi.creances_douteuses().to_csv('reports/kpi/creances_douteuses.csv', index=False)
    
    print("   ✅ synthese_daf.csv")
    print("   ✅ dso_par_client.csv")
    print("   ✅ creances_douteuses.csv")
    
    kpi.close()
    
    print("\n" + "=" * 75)
    print("✅ CALCUL DES KPI DAF TERMINÉ")
    print("=" * 75)