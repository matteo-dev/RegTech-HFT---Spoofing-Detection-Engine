# ⚖️ RegTech HFT - Spoofing Detection Engine

Moteur de régulation technologique (*RegTech*) et de surveillance de marché en temps réel conçu pour détecter les manipulations de carnet d'ordres à haute fréquence (*Spoofing*), appliqué au marché des quotas carbone.

## 🚀 Fonctionnalités Clés

1. **Architecture Asynchrone & File d'Attente :** Gestion des flux d'écritures massifs (*Heavy Writes*) via un système non-bloquant (`asyncio.Queue`) pour absorber la vélocité des acteurs HFT.
2. **Event Sourcing (SQLite) :** Journalisation immuable de chaque action et ordre dans une table d'audit conforme aux exigences réglementaires (AMF / MiFID II).
3. **Moteur de Conformité (HMM & CEP) :** Analyse comportementale par fenêtres glissantes en mémoire vive (RAM) croisant le ratio d'annulation (*CTR*) et la densité instantanée pour évaluer la probabilité de fraude via un modèle de Markov Caché.
4. **Bots Autonomes & Stress Test :** Générateurs de liquidité légitimes et agents malveillants furtifs simulant des attaques de spoofing, avec un "Bouton Rouge" pour injecter des scénarios de crise en direct.
5. **Tableau de Bord Streamlit :** Interface de contrôle séparant l'opérationnel temps réel (OLTP) de l'analytique de conformité (OLAP).

## English Below

Real-time RegTech and market surveillance engine designed to detect high-frequency order book manipulation (Spoofing), applied to the carbon credit market.

## 🚀 Key Features
1. **Asynchronous Architecture & Message Queue:** Management of massive write streams (Heavy Writes) via a non-blocking system (asyncio.Queue) to absorb HFT actor velocity.
2. **Event Sourcing (SQLite):** Immutable logging of every action and order in an audit table compliant with regulatory requirements (AMF / MiFID II).
3. **Compliance Engine (HMM & CEP):** Real-time in-memory (RAM) sliding window behavioral analysis crossing the cancellation-to-trade ratio (CTR) and instantaneous depth to evaluate fraud probability via a Hidden Markov Model.
4. **Autonomous Bots & Stress Testing:** Legitimate liquidity generators and stealthy malicious agents simulating spoofing attacks, complete with a "Red Button" to inject live crisis scenarios.
5. **Streamlit Dashboard:** Control interface separating real-time operational processing (OLTP) from compliance analytics (OLAP).

---

## 🛠️ Installation et Lancement

1. **Cloner le dépôt / Clone the reposit :**
   ```bash
   git clone [https://github.com/votre-nom-d-utilisateur/regtech-hft-spoofing-detection.git](https://github.com/votre-nom-d-utilisateur/regtech-hft-spoofing-detection.git)
   cd regtech-hft-spoofing-detection
2. **Installer les dépendances et lancer le backend et le frontend dans deux terminaux distincts / Install requirements and Run the backend and frontend in two separate terminals :**
   ```bash
   pip install - r requirements.txt
   uvicorn main:app --reload
   streamlit run dashboard.py
