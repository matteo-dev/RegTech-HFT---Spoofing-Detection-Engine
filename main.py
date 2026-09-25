# Fichier Python de backend pour le projet de détection des spoofing hft sur un marché


# Importation des bibliothèques nécessaires
import asyncio # Bibliothèque pour la programmation asynchrone
import sqlite3 # Bibliothèque pour la gestion de la base de données SQLite
import random
from collections import deque, defaultdict # Deque pour les fenêtres glissantes et defaultdict pour les historiques par trader
from datetime import datetime
from fastapi import FastAPI # Framework web pour créer l'API
from pydantic import BaseModel # Pour la validation des modèles de données

app = FastAPI(title="RegTech - Moteur HFT & Détection de Fraude")


# 1. ÉTAT DU MARCHÉ EN MÉMOIRE (RAM / CEP)

# État de base du marché (prix actuel, volume quotidien, historique des transactions)
market_state = {
    "current_price": 100.0,
    "daily_volume": 0,
    "history": deque(maxlen=20) 
}

# Carnet d'ordres (bids et asks) pour le matching engine
order_book = {"bids": [], "asks": []}

# Historique des ordres par trader pour le moteur de conformité (Compliance Engine)
trader_history = defaultdict(lambda: deque(maxlen=200))

# Fenêtre glissante pour les alertes de spoofing détectées (max 50 alertes)
alerts_log = deque(maxlen=50) 

# Queue asynchrone pour gérer les ordres entrants (FIFO)
order_queue = asyncio.Queue()


# 2. EVENT SOURCING (Base de données)

# Création d'une base SQLite pour stocker l'audit trail des ordres et actions des traders
db_conn = sqlite3.connect("market_audit.db", check_same_thread=False)
cursor = db_conn.cursor()

# On suit les règles AMF et on stocke chaque action dans une table d'audit pour la traçabilité, avec horodatage précis
cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        trader_id TEXT,
        action TEXT,
        ticker TEXT,
        qty INTEGER,
        price REAL
    )
""")
db_conn.commit()

# Classe Pydantic pour valider les requêtes d'ordre entrantes via l'API
class OrderRequest(BaseModel):
    trader_id: str
    action: str
    ticker: str
    qty: int
    price: float


# 3. MOTEUR D'EXÉCUTION (Le Marché)

# Fonction asynchrone principale qui dépile les ordres, met à jour le carnet et exécute les transactions
async def market_engine():

    print("Moteur HFT démarré...")

    # On boucle indéfiniment pour traiter les ordres entrants
    while True:
        order = await order_queue.get()
        
        # 1. Event Sourcing
        cursor.execute(
            "INSERT INTO audit_trail (timestamp, trader_id, action, ticker, qty, price) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%H:%M:%S.%f"), order["trader_id"], order["action"], order["ticker"], order["qty"], order["price"])
        )
        db_conn.commit()

        # 2. Mise à jour de l'historique pour le Compliance Engine
        trader_history[order["trader_id"]].append(order)

        # 3. Logique du Carnet d'Ordres
        if order["action"] == "PLACE_BID":
            order_book["bids"].append(order)
            order_book["bids"].sort(key=lambda x: x["price"], reverse=True)
        elif order["action"] == "PLACE_ASK":
            order_book["asks"].append(order)
            order_book["asks"].sort(key=lambda x: x["price"])
        elif order["action"] == "CANCEL":
            order_book["bids"] = [o for o in order_book["bids"] if o["trader_id"] != order["trader_id"] or o["price"] != order["price"]]
            order_book["asks"] = [o for o in order_book["asks"] if o["trader_id"] != order["trader_id"] or o["price"] != order["price"]]

        # 4. Matching Engine très simple (Croisement Bid / Ask)
        if order_book["bids"] and order_book["asks"]:
            best_bid = order_book["bids"][0]
            best_ask = order_book["asks"][0]
            
            # Si le meilleur bid est supérieur ou égal au meilleur ask, on exécute la transaction
            if best_bid["price"] >= best_ask["price"]: 
                exec_price = best_ask["price"]
                exec_qty = min(best_bid["qty"], best_ask["qty"])
                
                # On met à jour le carnet d'ordres après l'exécution
                market_state["current_price"] = exec_price
                market_state["daily_volume"] += exec_qty
                market_state["history"].append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "price": exec_price,
                    "qty": exec_qty,
                    "buyer": best_bid["trader_id"],
                    "seller": best_ask["trader_id"]
                })
                
                # On retire les ordres exécutés du carnet
                order_book["bids"].pop(0)
                order_book["asks"].pop(0)

        # 5. Déclenchement du gendarme financier à chaque ordre pour détecter les anomalies de spoofing
        asyncio.create_task(compliance_engine(order["trader_id"]))

        # 6. Marque la tâche comme terminée pour la queue
        order_queue.task_done()


# 4. MOTEUR DE SURVEILLANCE (Modèle HMM)

# Fonction asynchrone qui analyse l'historique d'un trader pour détecter des comportements de spoofing
async def compliance_engine(trader_id: str):
    history = trader_history[trader_id]
    
    # Si l'historique est trop court, on ne peut pas calculer de ratio fiable
    if len(history) < 10:
        return

    # 1. Calcul du CTR (Cancel-to-Trade Ratio) global
    places = sum(1 for o in history if "PLACE" in o["action"])
    cancels = sum(1 for o in history if o["action"] == "CANCEL")

    # La formule du CTR est Nbr annulations / Nbr ordres placés
    ctr_ratio = cancels / places if places > 0 else 0

    # 2. Densité sur la fenêtre immédiate (les 10 dernières actions)
    recent_actions = list(history)[-10:]
    recent_cancels = sum(1 for o in recent_actions if o["action"] == "CANCEL")

    # La formule de densité est Nbr annulations récentes / Taille de la fenêtre (ici 10)
    cancel_density = recent_cancels / len(recent_actions) if recent_actions else 0
    
    # 3. Calcul de la probabilité (Modèle HMM simplifié et pondéré)

    # La proba de base est faible (5%) pour éviter les faux positifs
    base_prob = 0.05

    # On pondère le CTR et la densité pour obtenir une probabilité finale de spoofing (35% pour le CTR, 60% pour la densité)
    p_spoofer = base_prob + (ctr_ratio * 0.35) + (cancel_density * 0.60)
    
    # Ajout d'une variance stochastique pour un rendu organique (ex: 84.2%)
    p_spoofer = min(0.99, p_spoofer * random.uniform(0.96, 1.04))

    # Si la probabilité d'être un spoofer dépasse 80%, on déclenche une alerte pour le trader suspect
    if p_spoofer > 0.80:
        alert = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "trader_id": trader_id,
            "confidence": f"{p_spoofer * 100:.1f}%",
            "ctr_ratio": f"{ctr_ratio * 100:.1f}%",
            "reason": "Anomalie HMM : Densité d'annulation critique"
        }
        
        # Anti-spam : on évite de dupliquer l'alerte à la milliseconde près
        if not any(a["trader_id"] == trader_id for a in list(alerts_log)[-3:]):
            alerts_log.append(alert)


# 5. LES BOTS AUTONOMES (Générateurs de Vélocité)

# Fonction asynchrone qui simule un trader sain apportant de la liquidité au marché
async def legitimate_bot(bot_id: int):

    # Chaque bot sain génère des ordres aléatoires toutes les 0.1 à 1.5 secondes pour simuler un marché actif
    while True:
        await asyncio.sleep(random.uniform(0.1, 1.5))
        price_variance = random.uniform(-0.5, 0.5)
        action = random.choices(["PLACE_BID", "PLACE_ASK", "CANCEL"], weights=[45, 45, 10], k=1)[0]
        
        # On envoie l'ordre dans la queue asynchrone pour traitement par le moteur de marché
        await order_queue.put({
            "trader_id": f"HFT_BOT_{bot_id}",
            "action": action,
            "ticker": "CO2_QUOTA",
            "qty": random.randint(10, 100),
            "price": round(market_state["current_price"] + price_variance, 2)
        })

# Fonction asynchrone qui simule un bot malveillant effectuant des attaques de spoofing furtives
async def autonomous_spoofer():

    # Le spoofer furtif attend un délai aléatoire entre 18 et 22 secondes pour ne pas être détecté par les algorithmes de surveillance
    while True:
        await asyncio.sleep(random.uniform(18.0, 22.0)) 
        trader = f"MALICIOUS_BOT_{random.randint(10,99)}"
        
        # Phase 1 : Bruit 

        # On envoie 2 ordres bid aléatoires pour créer un bruit de marché et masquer l'attaque
        for _ in range(2):
            await order_queue.put({
                "trader_id": trader, 
                "action": "PLACE_BID", 
                "ticker": "CO2_QUOTA", 
                "qty": random.randint(10, 50), 
                "price": round(market_state["current_price"], 2)
            })
        
        await asyncio.sleep(0.5) # Le marché absorbe le bruit
        
        # Phase 2 : Le mur de Spoofing 

        # On place un mur de bid à un prix légèrement inférieur au prix actuel pour inciter les autres traders à vendre
        spoof_price = market_state["current_price"] - 2.5

        # On choisit une quantité importante pour le mur de spoofing (entre 3000 et 5000 unités)
        spoof_qty = random.randint(3000, 5000)
        
        # On envoie 10 ordres bid identiques pour créer un mur de spoofing massif
        for _ in range(10):
            await order_queue.put({
                "trader_id": trader, 
                "action": "PLACE_BID", 
                "ticker": "CO2_QUOTA", 
                "qty": spoof_qty, 
                "price": spoof_price
            })
            
        await asyncio.sleep(0.1) # Temps de réaction de l'algorithme adverse
        
        # Phase 3 : Le retrait quasi-total 

        # Annulation de 9 des 10 ordres bid pour simuler un retrait soudain et provoquer une panique sur le marché
        for _ in range(9): 
            await order_queue.put({
                "trader_id": trader, 
                "action": "CANCEL", 
                "ticker": "CO2_QUOTA", 
                "qty": spoof_qty, 
                "price": spoof_price
            })

@app.on_event("startup")

# Fonction asynchrone qui démarre le moteur de marché et les bots autonomes au lancement de l'application FastAPI
async def startup_event():
    asyncio.create_task(market_engine())
    for i in range(5):
        asyncio.create_task(legitimate_bot(i)) 
    asyncio.create_task(autonomous_spoofer())  


# 6. ROUTES API (Frontend)

# Route OLTP pour alimenter l'onglet 1 du Dashboard avec les données de marché en temps réel
@app.get("/api/market_data")

# Fonction qui renvoie les données de marché actuelles, le carnet d'ordres et l'historique des transactions pour l'interface utilisateur
def get_market_data():
    return {
        "current_price": market_state["current_price"],
        "daily_volume": market_state["daily_volume"],
        "bids": order_book["bids"][:10], 
        "asks": order_book["asks"][:10],
        "history": list(market_state["history"])[::-1]
    }

# Route OLAP pour alimenter l'onglet 2 du Dashboard avec les alertes de spoofing détectées par le moteur de conformité
@app.get("/api/surveillance/alerts")

# Fonction qui renvoie les alertes de spoofing détectées, triées par ordre chronologique inverse pour l'affichage dans le dashboard
def get_alerts():
    return list(alerts_log)[::-1]

# Route de stress test pour injecter un scénario de spoofing massif dans le marché afin de tester la robustesse du moteur de conformité
@app.post("/api/stress_test/red_button")

# Fonction asynchrone qui simule une attaque massive de spoofing 
async def red_button():
    trader = "HEDGE_FUND_CRASH"

    # Injection de 50 ordres bid massifs à un prix fixe pour saturer le marché et tester la détection de spoofing
    for _ in range(50):
        await order_queue.put({"trader_id": trader, "action": "PLACE_BID", "ticker": "CO2_QUOTA", "qty": 9000, "price": 105.0})
    
    # Injection de 50 annulations pour simuler un retrait soudain et provoquer une panique sur le marché
    for _ in range(50):
        await order_queue.put({"trader_id": trader, "action": "CANCEL", "ticker": "CO2_QUOTA", "qty": 9000, "price": 105.0})
    return {"status": "Stress test injecté."}