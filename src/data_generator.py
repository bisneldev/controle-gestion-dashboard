"""
Générateur de données comptables réalistes pour une PME gabonaise
Conforme au plan comptable SYSCOHADA
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta


# =====================================================================
# CONFIGURATION
# =====================================================================
DEPARTEMENTS = {
    'Commercial': {'effectif': 15, 'budget_pct': 0.20},
    'Production': {'effectif': 25, 'budget_pct': 0.35},
    'RH':          {'effectif': 8,  'budget_pct': 0.12},
    'IT':          {'effectif': 7,  'budget_pct': 0.10},
    'Finance':     {'effectif': 10, 'budget_pct': 0.08},
    'Direction':   {'effectif': 5,  'budget_pct': 0.15},
}

# Postes budgétaires par département (avec comptes SYSCOHADA)
POSTES_BUDGET = {
    'Commercial': [
        ('Salaires', '661', 0.55),
        ('Commissions', '661', 0.15),
        ('Déplacements', '625', 0.12),
        ('Marketing', '623', 0.13),
        ('Fournitures', '604', 0.05),
    ],
    'Production': [
        ('Salaires', '661', 0.45),
        ('Matières premières', '601', 0.30),
        ('Énergie', '605', 0.10),
        ('Maintenance', '615', 0.10),
        ('Fournitures', '604', 0.05),
    ],
    'RH': [
        ('Salaires', '661', 0.60),
        ('Formation', '628', 0.15),
        ('Recrutement', '628', 0.10),
        ('Charges sociales', '664', 0.10),
        ('Fournitures', '604', 0.05),
    ],
    'IT': [
        ('Salaires', '661', 0.50),
        ('Licences', '612', 0.20),
        ('Matériel', '605', 0.15),
        ('Cloud/Serveurs', '612', 0.10),
        ('Formation', '628', 0.05),
    ],
    'Finance': [
        ('Salaires', '661', 0.60),
        ('Honoraires', '632', 0.15),
        ('Audit', '632', 0.10),
        ('Frais bancaires', '631', 0.10),
        ('Fournitures', '604', 0.05),
    ],
    'Direction': [
        ('Salaires', '661', 0.50),
        ('Déplacements', '625', 0.20),
        ('Représentation', '625', 0.15),
        ('Conseil', '632', 0.10),
        ('Fournitures', '604', 0.05),
    ],
}

MOIS_2025 = pd.date_range('2025-01-01', '2025-12-31', freq='MS').strftime('%Y-%m').tolist()
CA_ANNUEL = 2_000_000_000  # 2 Mds FCFA
BUDGET_ANNUEL = 1_500_000_000  # 1.5 Mds FCFA


# =====================================================================
# GÉNÉRATION DU BUDGET
# =====================================================================
def generer_budget():
    """Génère le budget annuel par département et poste"""
    np.random.seed(42)
    lignes = []
    
    for dept, config in DEPARTEMENTS.items():
        budget_dept = BUDGET_ANNUEL * config['budget_pct']
        postes = POSTES_BUDGET[dept]
        
        for poste_nom, compte, pct in postes:
            montant = budget_dept * pct
            # Ajouter une variabilité réaliste
            montant = round(montant * np.random.uniform(0.95, 1.05), 0)
            
            lignes.append({
                'departement': dept,
                'poste': poste_nom,
                'compte_syscohada': compte,
                'budget_annuel_fcfa': montant,
                'budget_mensuel_fcfa': round(montant / 12, 0),
            })
    
    df = pd.DataFrame(lignes)
    print(f"✅ Budget généré : {len(df)} lignes budgétaires")
    return df


# =====================================================================
# GÉNÉRATION DES DÉPENSES RÉELLES
# =====================================================================
def generer_depenses_reelles(df_budget):
    """
    Génère les dépenses mensuelles réelles.
    Simule des écarts budgétaires réalistes :
    - Dépassements sur certains postes (Production, IT)
    - Économies sur d'autres (Direction, RH)
    """
    np.random.seed(43)
    lignes = []
    
    # Profils de dérive par département
    profils = {
        'Commercial':   {'tendance': 1.02, 'variabilite': 0.08},  # +2%
        'Production':   {'tendance': 1.08, 'variabilite': 0.12},  # +8% (dépassement)
        'RH':           {'tendance': 0.97, 'variabilite': 0.05},  # -3% (économie)
        'IT':           {'tendance': 1.15, 'variabilite': 0.15},  # +15% (gros dépassement)
        'Finance':      {'tendance': 0.99, 'variabilite': 0.06},  # -1%
        'Direction':    {'tendance': 1.05, 'variabilite': 0.10},  # +5%
    }
    
    for _, row in df_budget.iterrows():
        dept = row['departement']
        poste = row['poste']
        budget_mensuel = row['budget_mensuel_fcfa']
        profil = profils[dept]
        
        for mois in MOIS_2025:
            # Écart mensuel réaliste
            tendance = profil['tendance']
            variabilite = np.random.normal(1, profil['variabilite'])
            
            # Saisonnalité (décembre plus cher, août plus calme)
            mois_num = int(mois.split('-')[1])
            saison = 1.0
            if mois_num == 12: saison = 1.20  # Décembre
            elif mois_num == 8: saison = 0.85  # Août (vacances)
            elif mois_num == 1: saison = 1.10  # Janvier (démarrage)
            
            depense = budget_mensuel * tendance * variabilite * saison
            depense = max(depense, 0)  # Pas de dépense négative
            
            lignes.append({
                'mois': mois,
                'departement': dept,
                'poste': poste,
                'compte_syscohada': row['compte_syscohada'],
                'budget_mensuel_fcfa': budget_mensuel,
                'depense_reelle_fcfa': round(depense, 0),
            })
    
    df = pd.DataFrame(lignes)
    print(f"✅ Dépenses réelles générées : {len(df)} lignes ({len(MOIS_2025)} mois × {len(df_budget)} postes)")
    return df


# =====================================================================
# GÉNÉRATION DES FACTURES CLIENTS
# =====================================================================
def generer_factures_clients(n_factures=500):
    """
    Génère les factures clients avec dates d'émission et d'encaissement.
    Permet de calculer le DSO (Days Sales Outstanding).
    """
    np.random.seed(44)
    
    clients = [
        'TOTAL Gabon', 'Perenco', 'COMILOG', 'CIMGABON', 
        'SEE Gabon', 'Air Liquide Gabon', 'Groupe CFAO', 
        'Sobraga', 'Gabon Telecom', 'BGFI Business', 
        'Moov Africa', 'Airtel Gabon', 'SEEG', 
        'Poste Gabon', 'Grands Moulins', 'Sucaf', 
        'Brasseries du Gabon', 'Sogara', 'Rougier Gabon',
        'CDC Gabon', 'Olam Gabon', 'Autre client'
    ]
    
    statuts = ['Payée', 'Payée', 'Payée', 'Payée', 'Payée',  # 70% payées
               'En retard', 'En retard',                       # 20% en retard
               'Impayée']                                       # 10% impayées
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    days_range = (end_date - start_date).days
    
    lignes = []
    for i in range(n_factures):
        # Date d'émission aléatoire en 2025
        emission = start_date + timedelta(days=np.random.randint(0, days_range))
        
        montant = np.random.lognormal(13.5, 0.8)  # ~700k FCFA médian
        montant = round(min(montant, 100_000_000), 0)
        
        statut = np.random.choice(statuts, p=[0.14, 0.14, 0.14, 0.14, 0.14,
                                                0.10, 0.10, 0.10])
        
        # Calcul date d'encaissement selon statut
        if statut == 'Payée':
            # Délai normal : 30-60 jours
            delai = np.random.randint(25, 65)
            encaissement = emission + timedelta(days=delai)
        elif statut == 'En retard':
            # Délai long : 90-180 jours
            delai = np.random.randint(90, 180)
            encaissement = emission + timedelta(days=delai)
        else:  # Impayée
            delai = None
            encaissement = None
        
        lignes.append({
            'facture_id': f'FAC-2025-{i+1:04d}',
            'client': np.random.choice(clients),
            'date_emission': emission.strftime('%Y-%m-%d'),
            'date_encaissement': encaissement.strftime('%Y-%m-%d') if encaissement else None,
            'montant_fcfa': montant,
            'statut': statut,
            'delai_jours': delai,
        })
    
    df = pd.DataFrame(lignes)
    print(f"✅ Factures clients générées : {len(df)} factures")
    return df


# =====================================================================
# GÉNÉRATION DES FACTURES FOURNISSEURS
# =====================================================================
def generer_factures_fournisseurs(n_factures=300):
    """
    Génère les factures fournisseurs avec dates de paiement.
    Permet de calculer le DPO (Days Payable Outstanding).
    """
    np.random.seed(45)
    
    fournisseurs = [
        'Total Gabon', 'SEE Gabon', 'Groupe CFAO', 'Sobraga',
        'Bureau Veritas', 'SGS Gabon', 'Airtel Business',
        'Groupe Bolloré', 'DHL Gabon', 'SAGA Gabon',
        'Auto Distribution', 'Groupe Adonis', 'Servair',
        'Clemessy Gabon', 'Adexium', 'Autre fournisseur'
    ]
    
    categories = ['Achats', 'Services', 'Énergie', 'Logistique', 
                  'Maintenance', 'Fournitures', 'Informatique']
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 12, 31)
    days_range = (end_date - start_date).days
    
    lignes = []
    for i in range(n_factures):
        emission = start_date + timedelta(days=np.random.randint(0, days_range))
        montant = np.random.lognormal(12.5, 0.7)
        montant = round(min(montant, 50_000_000), 0)
        
        # Délai de paiement : 30-90 jours (standard au Gabon)
        delai = np.random.randint(30, 90)
        paiement = emission + timedelta(days=delai)
        
        # Statut selon si la date de paiement est passée
        aujourdhui = datetime(2025, 12, 31)
        if paiement <= aujourdhui:
            statut = 'Payée'
        else:
            statut = 'À payer'
        
        lignes.append({
            'facture_id': f'FF-2025-{i+1:04d}',
            'fournisseur': np.random.choice(fournisseurs),
            'categorie': np.random.choice(categories),
            'date_emission': emission.strftime('%Y-%m-%d'),
            'date_paiement': paiement.strftime('%Y-%m-%d'),
            'montant_fcfa': montant,
            'statut': statut,
            'delai_jours': delai,
        })
    
    df = pd.DataFrame(lignes)
    print(f"✅ Factures fournisseurs générées : {len(df)} factures")
    return df


# =====================================================================
# SCRIPT PRINCIPAL
# =====================================================================
def sauvegarder(df, chemin):
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin, index=False, encoding='utf-8')
    print(f"   💾 {chemin} ({len(df)} lignes)")


if __name__ == '__main__':
    print("=" * 75)
    print("🏢 GÉNÉRATION DES DONNÉES COMPTABLES — PME GABONAISE")
    print("=" * 75)
    print(f"\n📅 Période : Janvier 2025 → Décembre 2025")
    print(f"🏢 Départements : {len(DEPARTEMENTS)}")
    print(f"💰 CA cible : {CA_ANNUEL/1e9:.1f} Mds FCFA")
    print(f"📊 Budget cible : {BUDGET_ANNUEL/1e9:.1f} Mds FCFA\n")
    
    # 1. Budget
    print("1️⃣ Génération du budget annuel...")
    df_budget = generer_budget()
    sauvegarder(df_budget, 'data/raw/budget_2025.csv')
    
    # 2. Dépenses réelles
    print("\n2️⃣ Génération des dépenses réelles...")
    df_depenses = generer_depenses_reelles(df_budget)
    sauvegarder(df_depenses, 'data/raw/depenses_reelles.csv')
    
    # 3. Factures clients
    print("\n3️⃣ Génération des factures clients...")
    df_clients = generer_factures_clients(n_factures=500)
    sauvegarder(df_clients, 'data/raw/factures_clients.csv')
    
    # 4. Factures fournisseurs
    print("\n4️⃣ Génération des factures fournisseurs...")
    df_fournisseurs = generer_factures_fournisseurs(n_factures=300)
    sauvegarder(df_fournisseurs, 'data/raw/factures_fournisseurs.csv')
    
    # ---- Statistiques rapides ----
    print("\n" + "=" * 75)
    print("📊 APERÇU DES DONNÉES GÉNÉRÉES")
    print("=" * 75)
    
    total_budget = df_budget['budget_annuel_fcfa'].sum()
    total_depenses = df_depenses['depense_reelle_fcfa'].sum()
    ecart = total_depenses - total_budget
    ecart_pct = ecart / total_budget * 100
    
    print(f"\n💰 BUDGET TOTAL : {total_budget:,.0f} FCFA")
    print(f"💸 DÉPENSES TOTALES : {total_depenses:,.0f} FCFA")
    print(f"📊 ÉCART GLOBAL : {ecart:+,.0f} FCFA ({ecart_pct:+.2f} %)")
    
    print(f"\n🧾 FACTURES CLIENTS :")
    print(f"   • Nombre : {len(df_clients)}")
    print(f"   • Montant total : {df_clients['montant_fcfa'].sum():,.0f} FCFA")
    print(f"   • Payées : {len(df_clients[df_clients['statut'] == 'Payée'])}")
    print(f"   • En retard : {len(df_clients[df_clients['statut'] == 'En retard'])}")
    print(f"   • Impayées : {len(df_clients[df_clients['statut'] == 'Impayée'])}")
    
    print(f"\n📄 FACTURES FOURNISSEURS :")
    print(f"   • Nombre : {len(df_fournisseurs)}")
    print(f"   • Montant total : {df_fournisseurs['montant_fcfa'].sum():,.0f} FCFA")
    
    print("\n" + "=" * 75)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 75)
    print("\n📁 Fichiers créés :")
    print("   • data/raw/budget_2025.csv")
    print("   • data/raw/depenses_reelles.csv")
    print("   • data/raw/factures_clients.csv")
    print("   • data/raw/factures_fournisseurs.csv")