import streamlit as st
import requests
import numpy as np
from datetime import datetime

# Configurazione grafica della pagina
st.set_page_config(page_title="Mondiali Advisor - Schedine Live", page_icon="⚽", layout="centered")

# HEADER E FIRMA
st.title("⚽ Mondiali Advisor")
st.markdown("*Software di Analisi Predittiva realizzato da **Salvatore Cosmano***")
st.markdown("---")

# Recupero automatico della chiave API nascosta nei Secrets
try:
    API_KEY = st.secrets["THE_ODDS_API_KEY"]
except Exception:
    st.error("❌ Errore di configurazione: Chiave API non trovata nei Secrets del server.")
    st.stop()

REGIO = "eu"          
MARKETS = "h2h,totals" 

@st.cache_data(ttl=600)  
def scarica_dati_live():
    sport_key = "soccer_fifa_world_cup" 
    url_odds = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params_odds = {'apiKey': API_KEY, 'regions': REGIO, 'markets': MARKETS, 'oddsFormat': 'decimal'}
    
    try:
        res = requests.get(url_odds, params=params_odds).json()
        if 'error' in res or len(res) == 0:
            sport_key = "soccer_international_matches"
            url_odds = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
            res = requests.get(url_odds, params=params_odds).json()
        return res
    except:
        return None

# --- PANNELLO DI CONTROLLO INTERATTIVO ---
st.sidebar.header("🎛️ Pannello Schedina")

tipo_strategia = st.sidebar.radio(
    "Scegli la strategia dell'algoritmo:",
    ("🟢 Cassa Sicura (Quote Fascia Bassa)", "🟡 Bilanciata (Fascia Media)", "🔴 Alta Quota (Fascia Speculativa)")
)

# MODIFICA 1: Esteso il limite massimo dello slider fino a 10 eventi
num_eventi = st.sidebar.slider("Quanti eventi vuoi in bolletta?", min_value=2, max_value=10, value=4)

if st.sidebar.button("🔄 Aggiorna Quote in Tempo Reale"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("⚡ Interrogando i server dei bookmaker..."):
    oracoli_data = scarica_dati_live()

if not oracoli_data or 'error' in oracoli_data:
    st.error("Impossibile caricare i palinsesti in questo momento. Riprova più tardi.")
    st.stop()

database_completo = []

# Ciclo analisi e smistamento dei match
for match in oracoli_data:
    home_team = match['home_team']
    away_team = match['away_team']
    
    # Estrazione e formattazione della data del match
    commence_time = match.get('commence_time', '')
    try:
        dt_obj = datetime.strptime(commence_time, "%Y-%m-%dT%H:%M:%SZ")
        data_giorno = dt_obj.strftime("%d/%m/%Y")
    except:
        data_giorno = "Prossimi Turni"
    
    if len(match['bookmakers']) == 0: continue
    market_list = match['bookmakers'][0]['markets']
    quota_1, quota_X, quota_2, quota_over = None, None, None, None
    
    for m in market_list:
        if m['key'] == 'h2h':
            for o in m['outcomes']:
                if o['name'] == home_team: quota_1 = o['price']
                elif o['name'] == away_team: quota_2 = o['price']
                else: quota_X = o['price']
        if m['key'] == 'totals':
            for o in m['outcomes']:
                if o['name'] == 'Over' and o.get('point') == 2.5: quota_over = o['price']

    if not quota_1 or not quota_2 or not quota_X: continue 

    p_1 = (1 / quota_1) * 100
    p_2 = (1 / quota_2) * 100
    p_X = (1 / quota_X) * 100

    # MODIFICA 3: Calcolo reale, matematico e preciso delle quote Doppia Chance (1 / Probabilità Complessiva)
    quota_1X = round(1 / ((p_1 + p_X) / 100), 2)
    quota_X2 = round(1 / ((p_2 + p_X) / 100), 2)
    
    # Di sicurezza blocchiamo i minimi per evitare arrotondamenti errati sotto l'1.01
    quota_1X = max(1.01, quota_1X)
    quota_X2 = max(1.01, quota_X2)

    # 🟢 Generazione Opzione Cassaforte
    if p_1 > 60:
        cassa_label, cassa_q, cassa_p = "1X DOPPIA CHANCE", quota_1X, min(98.0, p_1 + p_X)
    elif p_2 > 60:
        cassa_label, cassa_q, cassa_p = "X2 DOPPIA CHANCE", quota_X2, min(98.0, p_2 + p_X)
    else:
        cassa_label, cassa_q, cassa_p = "OVER 1.5 GOL", 1.22, 83.5

    # 🟡 Generazione Opzione Medio/Bilanciata
    if p_1 > p_2 and p_1 > 45:
        medio_label, medio_q, medio_p = "1 FISSO", quota_1, p_1
    elif p_2 > p_1 and p_2 > 45:
        medio_label, medio_q, medio_p = "2 FISSO", quota_2, p_2
    else:
        medio_label, medio_q, medio_p = "UNDER 3.5 GOL", 1.30, 70.0

    # 🔴 Generazione Opzione Alta Quota
    if quota_over and quota_over < 2.10:
        alta_label, alta_q, alta_p = "OVER 2.5 GOL", quota_over, (1 / quota_over) * 100
    else:
        alta_label, alta_q, alta_p = "ESITO PAREGGIO (X)", quota_X, p_X

    # Salviamo i dati nel database
    database_completo.append({
        "coppia": f"{home_team} vs {away_team}",
        "giorno": data_giorno,
        "lavagna": f"1: {quota_1} | X: {quota_X} | 2: {quota_2}",
        "cassa": {"giocata": cassa_label, "quota": cassa_q, "prob": cassa_p},
        "medio": {"giocata": medio_label, "quota": medio_q, "prob": medio_p},
        "alta": {"giocata": alta_label, "quota": alta_q, "prob": alta_p}
    })

# ==========================================
# 📊 SEZIONE 1: LA SCHEDINA DINAMICA (FINO A 10 EVENTI)
# ==========================================
st.header("💰 La Tua Schedina Personalizzata")
st.caption("Usa il pannello a sinistra per regolare il numero di partite e la propensione al rischio.")

candidati_filtrati = []
chiave_strategia = "cassa" if "🟢" in tipo_strategia else ("medio" if "🟡" in tipo_strategia else "alta")

for d in database_completo:
    candidati_filtrati.append({
        "match": d["coppia"],
        "giocata": d[chiave_strategia]["giocata"],
        "quota": d[chiave_strategia]["quota"],
        "prob": d[chiave_strategia]["prob"]
    })

candidati_filtrati = sorted(candidati_filtrati, key=lambda x: x['prob'], reverse=True)
schedina_utente = candidati_filtrati[:num_eventi]

if len(schedina_utente) < 2:
    st.warning("⚠️ Troppi pochi eventi nel palinsesto attuale per comporre una bolletta.")
else:
    quota_totale = 1.0
    with st.container():
        for i, part in enumerate(schedina_utente, 1):
            st.info(f"📌 **{i}. {part['match']}** \n\n Esito: `{part['giocata']}` | Quota: **{part['quota']:.2f}** (Affidabilità: {part['prob']:.1f}%)")
            quota_totale *= part['quota']
        
        st.success(f"🔥 **QUOTA TOTALE MOLTIPLICATORE: {quota_totale:.2f}**")

# ==========================================
# MODIFICA 2: DIVISIONE DELLO STUDIO IN GIORNATE DEI GIRONI
# ==========================================
st.markdown("---")
st.header("📚 Il Centro Studi dell'Algoritmo")
st.write("Filtra le partite in base ai giorni del calendario ufficiale:")

# Estraiamo tutti i giorni unici in modo ordinato
giorni_disponibili = sorted(list(set([d["giorno"] for d in database_completo])))

for giorno in giorni_disponibili:
    st.subheader(f"📅 Partite del {giorno}")
    
    # Cicliamo solo i match che appartengono a questa specifica giornata
    for d in database_completo:
        if d["giorno"] == giorno:
            with st.expander(f"🏟️ {d['coppia']}"):
                st.write(f"**Quote di Partenza dei Bookmaker:** `{d['lavagna']}`")
                col1, col2, col3 = st.columns(3)
                col1.metric("🟢 CASSAFORTE", d["cassa"]["giocata"], f"{d['cassa']['quota']:.2f}")
                col2.metric("🟡 MEDIO", d["medio"]["giocata"], f"{d['medio']['quota']:.2f}")
                col3.metric("🔴 ALTA QUOTA", d["alta"]["giocata"], f"{d['alta']['quota']:.2f}")

# FOOTER DI COPYRIGHT
st.markdown("---")
st.caption("© 2026 Mondiali Advisor | Sviluppato e ingegnerizzato da Salvatore Cosmano. Tutti i diritti riservati.")
