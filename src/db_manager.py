"""
Gestion de la base SQLite pour le contrôle de gestion
"""
import sqlite3
import pandas as pd
from pathlib import Path


class DBManager:
    """Gestionnaire de la base SQLite"""
    
    def __init__(self, db_path='database/controle_gestion.db'):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        print(f"🔗 Connexion à : {db_path}")
    
    def charger_dataframe(self, df, table):
        """Charge un DataFrame dans une table SQLite"""
        df.to_sql(table, self.conn, if_exists='replace', index=False)
        n = self.query(f"SELECT COUNT(*) as n FROM {table}").iloc[0]['n']
        print(f"   ✅ {table:25s} : {n:,} lignes")
    
    def query(self, sql):
        """Exécute une requête SQL"""
        return pd.read_sql_query(sql, self.conn)
    
    def tables(self):
        """Liste les tables existantes"""
        return self.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    
    def close(self):
        self.conn.close()


# =====================================================================
# DIAGNOSTIC
# =====================================================================
def diagnostic_complet(df_budget, df_depenses, df_clients, df_fournisseurs):
    """Diagnostic complet des 4 datasets"""
    print("=" * 75)
    print("📊 DIAGNOSTIC DES DONNÉES DE CONTRÔLE DE GESTION")
    print("=" * 75)
    
    # ---- 1. Dimensions ----
    print(f"\n1️⃣ DIMENSIONS")
    print(f"   • Budget           : {len(df_budget):,} lignes × {df_budget.shape[1]} colonnes")
    print(f"   • Dépenses réelles : {len(df_depenses):,} lignes × {df_depenses.shape[1]} colonnes")
    print(f"   • Factures clients : {len(df_clients):,} lignes × {df_clients.shape[1]} colonnes")
    print(f"   • Factures fourn.  : {len(df_fournisseurs):,} lignes × {df_fournisseurs.shape[1]} colonnes")
    
    # ---- 2. Valeurs manquantes ----
    print(f"\n2️⃣ VALEURS MANQUANTES")
    for nom, df in [
        ('Budget', df_budget),
        ('Dépenses', df_depenses),
        ('Factures clients', df_clients),
        ('Factures fournisseurs', df_fournisseurs),
    ]:
        missing = df.isnull().sum().sum()
        if missing == 0:
            print(f"   ✅ {nom:25s} : aucune")
        else:
            print(f"   ⚠️  {nom:25s} : {missing} valeurs manquantes")
    
    # ---- 3. Doublons ----
    print(f"\n3️⃣ DOUBLONS")
    for nom, df in [
        ('Budget', df_budget),
        ('Dépenses', df_depenses),
        ('Factures clients', df_clients),
        ('Factures fournisseurs', df_fournisseurs),
    ]:
        n = df.duplicated().sum()
        status = "✅" if n == 0 else "⚠️"
        print(f"   {status} {nom:25s} : {n}")
    
    # ---- 4. Analyse budgétaire ----
    print(f"\n4️⃣ ANALYSE BUDGÉTAIRE GLOBALE")
    total_budget = df_budget['budget_annuel_fcfa'].sum()
    total_depenses = df_depenses['depense_reelle_fcfa'].sum()
    ecart = total_depenses - total_budget
    ecart_pct = ecart / total_budget * 100
    
    print(f"   • Budget total     : {total_budget:>15,.0f} FCFA")
    print(f"   • Dépenses totales : {total_depenses:>15,.0f} FCFA")
    print(f"   • Écart global     : {ecart:>+15,.0f} FCFA ({ecart_pct:+.2f} %)")
    
    # ---- 5. Répartition par département ----
    print(f"\n5️⃣ RÉPARTITION DU BUDGET PAR DÉPARTEMENT")
    repart = (
        df_budget.groupby('departement')['budget_annuel_fcfa']
        .sum().sort_values(ascending=False).reset_index()
    )
    repart['pct'] = (repart['budget_annuel_fcfa'] / total_budget * 100).round(2)
    for _, row in repart.iterrows():
        print(f"   • {row['departement']:12s} : {row['budget_annuel_fcfa']:>15,.0f} FCFA "
              f"({row['pct']:5.2f} %)")
    
    # ---- 6. Analyse des factures clients ----
    print(f"\n6️⃣ FACTURES CLIENTS — ANALYSE")
    ca_total = df_clients['montant_fcfa'].sum()
    print(f"   • CA total         : {ca_total:,.0f} FCFA")
    print(f"   • Nombre factures  : {len(df_clients)}")
    print(f"   • Montant moyen    : {df_clients['montant_fcfa'].mean():,.0f} FCFA")
    
    repart_statut = df_clients.groupby('statut').agg(
        nb=('facture_id', 'count'),
        montant=('montant_fcfa', 'sum')
    ).reset_index()
    repart_statut['pct_nb'] = (repart_statut['nb'] / len(df_clients) * 100).round(2)
    repart_statut['pct_montant'] = (repart_statut['montant'] / ca_total * 100).round(2)
    
    print(f"\n   Répartition par statut :")
    for _, row in repart_statut.iterrows():
        print(f"   • {row['statut']:12s} : {row['nb']:>3} factures "
              f"({row['pct_nb']:5.2f} % du nb) — {row['montant']:>15,.0f} FCFA "
              f"({row['pct_montant']:5.2f} %)")
    
    # Délai moyen d'encaissement
    df_payees = df_clients[df_clients['delai_jours'].notna()]
    print(f"\n   • Délai moyen d'encaissement : {df_payees['delai_jours'].mean():.1f} jours")
    print(f"   • Délai médian              : {df_payees['delai_jours'].median():.1f} jours")
    
    # ---- 7. Analyse des factures fournisseurs ----
    print(f"\n7️⃣ FACTURES FOURNISSEURS — ANALYSE")
    achats_total = df_fournisseurs['montant_fcfa'].sum()
    print(f"   • Achats total     : {achats_total:,.0f} FCFA")
    print(f"   • Nombre factures  : {len(df_fournisseurs)}")
    print(f"   • Délai moyen paiement : {df_fournisseurs['delai_jours'].mean():.1f} jours")
    
    repart_cat = df_fournisseurs.groupby('categorie').agg(
        nb=('facture_id', 'count'),
        montant=('montant_fcfa', 'sum')
    ).reset_index().sort_values('montant', ascending=False)
    
    print(f"\n   Répartition par catégorie :")
    for _, row in repart_cat.head(5).iterrows():
        pct = row['montant'] / achats_total * 100
        print(f"   • {row['categorie']:15s} : {row['montant']:>15,.0f} FCFA ({pct:5.2f} %)")
    
    print("\n" + "=" * 75)
    print("✅ Diagnostic terminé")
    print("=" * 75)
    
    return {
        'total_budget': total_budget,
        'total_depenses': total_depenses,
        'ecart_global': ecart,
        'ecart_pct': ecart_pct,
        'ca_total': ca_total,
        'achats_total': achats_total,
    }


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
if __name__ == '__main__':
    print("🔄 Chargement des données brutes...")
    
    df_budget = pd.read_csv('data/raw/budget_2025.csv')
    df_depenses = pd.read_csv('data/raw/depenses_reelles.csv')
    df_clients = pd.read_csv('data/raw/factures_clients.csv')
    df_fournisseurs = pd.read_csv('data/raw/factures_fournisseurs.csv')
    
    print(f"✅ 4 fichiers chargés\n")
    
    # Diagnostic
    diag = diagnostic_complet(df_budget, df_depenses, df_clients, df_fournisseurs)
    
    # Chargement en base
    print("\n🗄️  Chargement en base SQLite...")
    db = DBManager()
    db.charger_dataframe(df_budget, 'budget')
    db.charger_dataframe(df_depenses, 'depenses')
    db.charger_dataframe(df_clients, 'factures_clients')
    db.charger_dataframe(df_fournisseurs, 'factures_fournisseurs')
    
    print("\n📋 Tables créées :")
    print(db.tables().to_string(index=False))
    
    db.close()
    
    print("\n" + "=" * 75)
    print("✅ BASE SQLITE CRÉÉE")
    print("=" * 75)
    print(f"📁 database/controle_gestion.db")