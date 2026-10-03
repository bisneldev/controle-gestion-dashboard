"""
Dashboard de Contrôle de Gestion
Contexte : PME gabonaise — Direction Administrative et Financière
"""
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sqlite3


# =====================================================================
# CHARGEMENT DES DONNÉES
# =====================================================================
DB_PATH = 'database/controle_gestion.db'
conn = sqlite3.connect(DB_PATH)

df_budget = pd.read_sql_query("SELECT * FROM budget", conn)
df_depenses = pd.read_sql_query("SELECT * FROM depenses", conn)
df_clients = pd.read_sql_query("SELECT * FROM factures_clients", conn)
df_fournisseurs = pd.read_sql_query("SELECT * FROM factures_fournisseurs", conn)
conn.close()

print(f"✅ Données chargées :")
print(f"   • Budget : {len(df_budget)} lignes")
print(f"   • Dépenses : {len(df_depenses)} lignes")
print(f"   • Clients : {len(df_clients)} lignes")
print(f"   • Fournisseurs : {len(df_fournisseurs)} lignes")


# =====================================================================
# CALCULS PRÉ-AGRÉGÉS
# =====================================================================
# Budget vs Réel par département
budget_dept = df_budget.groupby('departement')['budget_annuel_fcfa'].sum()
depense_dept = df_depenses.groupby('departement')['depense_reelle_fcfa'].sum()
df_dept = pd.DataFrame({
    'departement': budget_dept.index,
    'budget': budget_dept.values,
    'depense': depense_dept.values,
})
df_dept['ecart'] = df_dept['depense'] - df_dept['budget']
df_dept['ecart_pct'] = (df_dept['ecart'] / df_dept['budget'] * 100).round(2)
df_dept = df_dept.sort_values('ecart_pct', ascending=False)

# Écarts mensuels
df_mois = df_depenses.groupby('mois').agg(
    budget=('budget_mensuel_fcfa', 'sum'),
    depense=('depense_reelle_fcfa', 'sum')
).reset_index()
df_mois['ecart_pct'] = ((df_mois['depense'] - df_mois['budget']) / df_mois['budget'] * 100).round(2)

# KPIs globaux
total_budget = df_budget['budget_annuel_fcfa'].sum()
total_depense = df_depenses['depense_reelle_fcfa'].sum()
ecart_global = total_depense - total_budget
ecart_pct = ecart_global / total_budget * 100

ca_total = df_clients['montant_fcfa'].sum()
ca_encaisse = df_clients[df_clients['statut'] == 'Payée']['montant_fcfa'].sum()
ca_retard = df_clients[df_clients['statut'] == 'En retard']['montant_fcfa'].sum()
ca_impaye = df_clients[df_clients['statut'] == 'Impayée']['montant_fcfa'].sum()
taux_recouvrement = ca_encaisse / ca_total * 100

dso = df_clients[df_clients['delai_jours'].notna()]['delai_jours'].mean()
dpo = df_fournisseurs['delai_jours'].mean()
bfr = (ca_retard + ca_impaye) - df_fournisseurs[df_fournisseurs['statut'] == 'À payer']['montant_fcfa'].sum()


# =====================================================================
# PALETTE
# =====================================================================
COLORS = {
    'primaire': '#1f3a5f',
    'success': '#2a9d8f',
    'accent': '#e63946',
    'warning': '#f4a261',
    'light': '#f5f7fa',
    'dark': '#2c3e50',
}
DECISION_COLORS = {'Payée': COLORS['success'], 'En retard': COLORS['warning'], 'Impayée': COLORS['accent']}


# =====================================================================
# KPI CARD
# =====================================================================
def kpi_card(titre, valeur, sous_titre="", couleur=None):
    couleur = couleur or COLORS['primaire']
    return html.Div([
        html.P(titre, style={
            'margin': 0, 'color': '#7a8899', 'fontSize': '11px',
            'fontWeight': '600', 'letterSpacing': '0.5px',
            'textTransform': 'uppercase'
        }),
        html.H2(valeur, style={
            'margin': '8px 0 4px 0', 'color': couleur,
            'fontSize': '22px', 'fontWeight': '700'
        }),
        html.P(sous_titre, style={
            'margin': 0, 'color': '#a0aec0', 'fontSize': '11px'
        }),
    ], style={
        'background': 'white',
        'padding': '16px 18px',
        'borderRadius': '12px',
        'boxShadow': '0 2px 12px rgba(0,0,0,0.06)',
        'borderLeft': f'4px solid {couleur}',
        'flex': 1,
        'minWidth': '180px'
    })


# =====================================================================
# APPLICATION
# =====================================================================
app = dash.Dash(__name__, title="Contrôle de Gestion")
server = app.server

app.layout = html.Div([

    # HEADER
    html.Div([
        html.Div([
            html.H1("📊 Contrôle de Gestion",
                    style={'margin': 0, 'color': 'white',
                           'fontSize': '26px', 'fontWeight': '700'}),
            html.P("Tableau de bord Direction — PME Gabon 2025",
                   style={'margin': '5px 0 0 0', 'color': '#b8c5d6',
                          'fontSize': '14px'}),
        ], style={'flex': 1}),
        html.Div([
            html.P("📅 Exercice 2025",
                   style={'color': 'white', 'margin': 0,
                          'fontSize': '14px', 'fontWeight': '600'}),
            html.P(f"💰 CA : {ca_total/1e6:.0f} M FCFA",
                   style={'color': '#b8c5d6', 'margin': '4px 0 0 0',
                          'fontSize': '13px'}),
        ], style={'textAlign': 'right'})
    ], style={
        'background': f'linear-gradient(90deg, {COLORS["primaire"]}, #2c5282)',
        'padding': '25px 40px',
        'display': 'flex',
        'alignItems': 'center'
    }),

    # KPIs
    html.Div([
        kpi_card("💰 Budget total", f"{total_budget/1e6:.0f} M",
                 "FCFA", COLORS['primaire']),
        kpi_card("💸 Dépenses", f"{total_depense/1e6:.0f} M",
                 f"{ecart_pct:+.2f} % vs budget",
                 COLORS['accent'] if ecart_pct > 0 else COLORS['success']),
        kpi_card("✅ Taux recouvrement", f"{taux_recouvrement:.1f} %",
                 f"CA : {ca_total/1e6:.0f} M FCFA", COLORS['success']),
        kpi_card("📅 DSO", f"{dso:.1f} j",
                 "Délai encaissement", 
                 COLORS['success'] if dso < 45 else COLORS['warning']),
        kpi_card("📊 BFR", f"{bfr/1e6:+.0f} M",
                 "FCFA à financer",
                 COLORS['accent'] if bfr > 0 else COLORS['success']),
    ], style={
        'display': 'flex', 'gap': '18px',
        'padding': '25px 40px', 'flexWrap': 'wrap'
    }),

    # LIGNE 1 : Budget vs Réel par département + Écarts mensuels
    html.Div([
        html.Div(dcc.Graph(id='graph-dept'),
                 style={'flex': 1, 'minWidth': '450px'}),
        html.Div(dcc.Graph(id='graph-mois'),
                 style={'flex': 1, 'minWidth': '450px'}),
    ], style={
        'display': 'flex', 'gap': '20px',
        'padding': '0 40px 20px 40px', 'flexWrap': 'wrap'
    }),

    # LIGNE 2 : Statuts clients + Top clients lents
    html.Div([
        html.Div(dcc.Graph(id='graph-clients'),
                 style={'flex': 1, 'minWidth': '450px'}),
        html.Div(dcc.Graph(id='graph-clients-lents'),
                 style={'flex': 1, 'minWidth': '450px'}),
    ], style={
        'display': 'flex', 'gap': '20px',
        'padding': '0 40px 20px 40px', 'flexWrap': 'wrap'
    }),

    # TABLEAU TOP DÉPASSEMENTS
    html.Div([
        html.H3("🚨 Top 10 des dépassements budgétaires",
                style={'color': COLORS['primaire'],
                       'padding': '0 40px', 'margin': '20px 0 10px 0'}),
        html.Div(id='tableau-depassements',
                 style={'padding': '0 40px 40px 40px'})
    ]),

    # FOOTER
    html.Div([
        html.P("📌 Dashboard Contrôle de Gestion — Python, SQL, Plotly Dash",
               style={'color': '#718096', 'fontSize': '12px',
                      'textAlign': 'center', 'margin': 0}),
    ], style={'padding': '20px', 'background': '#e2e8f0'})

], style={
    'fontFamily': "'Segoe UI', Arial, sans-serif",
    'background': COLORS['light'],
    'minHeight': '100vh',
    'margin': 0
})


# =====================================================================
# CALLBACK (pour interactivité future — filtres)
# =====================================================================
@app.callback(
    [Output('graph-dept', 'figure'),
     Output('graph-mois', 'figure'),
     Output('graph-clients', 'figure'),
     Output('graph-clients-lents', 'figure'),
     Output('tableau-depassements', 'children')],
    [Input('graph-dept', 'id')]  # trigger initial
)
def update_dashboard(_):
    # ---- Graph 1 : Budget vs Réel par département ----
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        name='Budget',
        x=df_dept['departement'],
        y=df_dept['budget']/1e6,
        marker_color=COLORS['primaire'],
        text=[f'{v/1e6:.0f} M' for v in df_dept['budget']],
        textposition='outside'
    ))
    fig1.add_trace(go.Bar(
        name='Dépenses réelles',
        x=df_dept['departement'],
        y=df_dept['depense']/1e6,
        marker_color=COLORS['accent'],
        text=[f'{v/1e6:.0f} M' for v in df_dept['depense']],
        textposition='outside'
    ))
    fig1.update_layout(
        title="💰 Budget vs Réel par département",
        barmode='group',
        template='plotly_white',
        height=400,
        yaxis_title="Millions FCFA",
        legend=dict(orientation='h', y=1.1)
    )
    
    # ---- Graph 2 : Écarts mensuels ----
    colors_mois = [COLORS['accent'] if x > 0 else COLORS['success'] 
                   for x in df_mois['ecart_pct']]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_mois['mois'],
        y=df_mois['ecart_pct'],
        marker_color=colors_mois,
        text=[f'{x:+.1f}%' for x in df_mois['ecart_pct']],
        textposition='outside'
    ))
    fig2.update_layout(
        title="📅 Écarts budgétaires mensuels",
        template='plotly_white',
        height=400,
        yaxis_title="Écart (%)",
        xaxis_title="",
        showlegend=False
    )
    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
    
    # ---- Graph 3 : Statuts clients ----
    statut_agg = df_clients.groupby('statut').agg(
        nb=('facture_id', 'count'),
        montant=('montant_fcfa', 'sum')
    ).reset_index()
    
    fig3 = go.Figure()
    fig3.add_trace(go.Pie(
        labels=statut_agg['statut'],
        values=statut_agg['montant']/1e6,
        marker_colors=[DECISION_COLORS.get(s, '#ccc') for s in statut_agg['statut']],
        hole=0.5,
        textinfo='label+percent',
        hovertemplate='%{label}<br>%{value:.1f} M FCFA<br>%{percent}<extra></extra>'
    ))
    fig3.update_layout(
        title="🧾 Répartition des créances clients (M FCFA)",
        template='plotly_white',
        height=400
    )
    
    # ---- Graph 4 : Top clients lents ----
    df_lents = df_clients[df_clients['delai_jours'].notna()].groupby('client').agg(
        delai=('delai_jours', 'mean'),
        nb=('facture_id', 'count'),
        taux_impayes=('statut', lambda x: (x == 'Impayée').sum() / len(x) * 100)
    ).reset_index()
    df_lents = df_lents[df_lents['nb'] >= 5].nlargest(8, 'delai').sort_values('delai')
    
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=df_lents['delai'],
        y=df_lents['client'],
        orientation='h',
        marker_color=df_lents['delai'],
        marker_colorscale='Reds',
        text=[f'{d:.1f} j' for d in df_lents['delai']],
        textposition='outside'
    ))
    fig4.update_layout(
        title="🐢 Top 8 clients avec les délais les plus longs",
        template='plotly_white',
        height=400,
        xaxis_title="Délai moyen (jours)",
        coloraxis_showscale=False
    )
    
    # ---- Tableau Top dépassements ----
    budget_agg = df_budget.groupby(['departement', 'poste'])['budget_annuel_fcfa'].sum().reset_index()
    depense_agg = df_depenses.groupby(['departement', 'poste'])['depense_reelle_fcfa'].sum().reset_index()
    merged = budget_agg.merge(depense_agg, on=['departement', 'poste'])
    merged['ecart'] = merged['depense_reelle_fcfa'] - merged['budget_annuel_fcfa']
    merged['ecart_pct'] = (merged['ecart'] / merged['budget_annuel_fcfa'] * 100).round(2)
    top = merged.nlargest(10, 'ecart')
    
    top_display = top.copy()
    top_display['Budget'] = top_display['budget_annuel_fcfa'].apply(lambda x: f"{x/1e6:.1f} M")
    top_display['Dépense'] = top_display['depense_reelle_fcfa'].apply(lambda x: f"{x/1e6:.1f} M")
    top_display['Écart'] = top_display['ecart'].apply(lambda x: f"+{x/1e6:.1f} M")
    top_display['Écart %'] = top_display['ecart_pct'].apply(lambda x: f"+{x:.2f} %")
    top_display = top_display.rename(columns={'departement': 'Département', 'poste': 'Poste'})
    
    tableau = dash_table.DataTable(
        data=top_display[['Département', 'Poste', 'Budget', 'Dépense', 'Écart', 'Écart %']].to_dict('records'),
        columns=[{'name': c, 'id': c} for c in ['Département', 'Poste', 'Budget', 'Dépense', 'Écart', 'Écart %']],
        style_cell={
            'textAlign': 'left', 'padding': '12px 15px',
            'fontFamily': "'Segoe UI', Arial, sans-serif",
            'fontSize': '13px'
        },
        style_header={
            'backgroundColor': COLORS['primaire'],
            'color': 'white', 'fontWeight': 'bold',
            'fontSize': '12px', 'textTransform': 'uppercase'
        },
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
            {'if': {'column_id': 'Écart'}, 'color': COLORS['accent'], 'fontWeight': 'bold'},
        ],
        style_as_list_view=True,
    )
    
    return fig1, fig2, fig3, fig4, tableau


# =====================================================================
# LANCEMENT
# =====================================================================
if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 Dashboard Contrôle de Gestion démarré")
    print("=" * 70)
    print("👉 Ouvre ton navigateur : http://127.0.0.1:8052")
    print("⛔ Pour arrêter : Ctrl + C")
    print("=" * 70 + "\n")
    app.run(debug=True, port=8052)