# Fichier Python de frontend/streamlit pour le projet de détection des spoofing hft sur un marché


# Importation des bibliothèques nécessaires
import streamlit as st # Bibliothèque pour créer des applications web interactives en Python
import requests # Bibliothèque pour effectuer des requêtes HTTP vers le backend FastAPI
import pandas as pd
import time


# Configuration de la page
st.set_page_config(page_title="RegTech HFT - Spoofing Detection", layout="wide", page_icon="⚖️")

API_URL = "http://127.0.0.1:8000/api"


# Fonctions utilitaires

# Fonction pour récupérer les données du backend FastAPI
def fetch_data(endpoint):
    try:
        response = requests.get(f"{API_URL}/{endpoint}", timeout=1.5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None

# Fonction pour déclencher l'attaque de spoofing via le bouton rouge
def trigger_red_button():
    try:
        requests.post(f"{API_URL}/stress_test/red_button")
        st.toast("🚨 BOUTON ROUGE : Attaque HFT massive injectée dans la file d'attente !")
    except:
        st.error("Impossible de joindre le serveur pour lancer l'attaque.")


# Entête et description de l'application

st.title("⚖️ Moteur RegTech - Détection de Spoofing HFT")
st.markdown("Surveillance de marché en temps réel (Complex Event Processing) par modèle HMM.")

# Vérification de la connexion au backend
market_data = fetch_data("market_data")
if not market_data:
    st.error("Serveur Backend (FastAPI) injoignable. Lance le moteur asynchrone pour voir les bots en action.")
    st.stop() # Arrête l'exécution si le serveur est hors ligne, évitant les erreurs de données

# Création des deux onglets pour séparer l'opérationnel (OLTP) de l'analytique (OLAP)
tab_live, tab_compliance = st.tabs(["📈 Marché Live (OLTP)", "🚨 Conformité & Alertes (OLAP)"])


# ONGLET 1 : MARCHÉ LIVE (OLTP)

with tab_live:
    st.markdown("### 📊 Carnet d'Ordres et Flux d'Exécution en Temps Réel")
    
    # Affichage des métriques globales du sous-jacent 
    col1, col2, col3 = st.columns(3)
    current_price = market_data.get("current_price", 100.0)
    volume = market_data.get("daily_volume", 0)
    
    col1.metric("Prix Actuel (CO2)", f"{current_price:.2f} €")
    col2.metric("Volume Échangé", f"{volume} lots")
    col3.metric("État du Réseau", "Fluide (Asynchrone)", "0 ms latence")

    st.divider()
    
    col_bids, col_asks, col_trades = st.columns([1, 1, 1.5])
    
    # Affichage des données du carnet d'ordres, ici les bids
    with col_bids:
        st.subheader("🟩 Acheteurs (Bids)")
        bids = market_data.get("bids", [])
        if bids:
            st.dataframe(pd.DataFrame(bids), use_container_width=True, hide_index=True)
    
    # Affichage des données du carnet d'ordres, ici les asks
    with col_asks:
        st.subheader("🟥 Vendeurs (Asks)")
        asks = market_data.get("asks", [])
        if asks:
            st.dataframe(pd.DataFrame(asks), use_container_width=True, hide_index=True)

    # Affichage des dernières transactions validées
    with col_trades:
        st.subheader("📜 Dernières Transactions Validées")
        history = market_data.get("history", [])
        if history:
            df_history = pd.DataFrame(history)
            st.dataframe(df_history, use_container_width=True, hide_index=True, height=350)


# ONGLET 2 : CONFORMITÉ (OLAP)

with tab_compliance:
    st.markdown("### 👁️ Monitoring AMF - Analyse des Fenêtres Glissantes")
    st.markdown("Cette section lit les alertes générées par le moteur asynchrone sans ralentir le marché.")
    
    col_action, col_alerts = st.columns([1, 3])
    
    # Ajout d'un bouton rouge pour simuler une attaque de spoofing et injecter des événements contradictoires
    with col_action:
        st.button(
            "🔴 Attaque Spoofing", 
            type="primary", 
            use_container_width=True, 
            on_click=trigger_red_button
        )
        st.caption("Injecte instantanément 100 événements contradictoires dans le carnet d'ordres.")
    
    # Affichage des alertes de spoofing détectées par le moteur asynchrone
    with col_alerts:
        alerts_data = fetch_data("surveillance/alerts")
        if alerts_data and len(alerts_data) > 0:
            st.error(f"⚠️ {len(alerts_data)} entité(s) malveillante(s) détectée(s) en mémoire RAM !")
            df_alerts = pd.DataFrame(alerts_data)

            # Affichage clair du trader suspect et de la confiance du modèle mathématique
            st.dataframe(
                df_alerts[["timestamp", "trader_id", "confidence", "ctr_ratio", "reason"]], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.success("✅ Aucun comportement suspect détecté. Ratio annulation/exécution sain.")


# BOUCLE DE RAFRAÎCHISSEMENT TEMPS RÉEL

# Pause d'une seconde puis relance complète du script pour créer une boucle de rafraîchissement infinie.
time.sleep(1)
st.rerun()