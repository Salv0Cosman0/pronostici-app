import streamlit as st
import requests
import numpy as np

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

@st.cache_data(ttl=600)  # Ridotto a 10 minuti per maggiore reattività live
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

# --- PANNELLO DI CONTROLLO INTERATTIVO (In cima alla pagina) ---
st.sidebar.header("🎛️ Pannello Schedina")

# 1. Filtro tipo di rischio
tipo_strategia = st.sidebar.radio(
    "Scegli la strategia dell'algoritmo:",
    ("🟢 Cassa Sicura (Quote Fascia Bassa)", "🟡 Bilanciata (Fascia Media)", "🔴 Alta Quota (Fascia Speculativa)")
)

# 2. Filtro numero eventi
num_eventi = st.sidebar.slider("Quanti eventi vuoi in bolletta?", min_value=2, max_value=5, value=3)

# 3. Pulsante di aggiornamento quote live
if st.sidebar.button("🔄 Aggiorna Quote in Tempo Reale"):
    st.cache_data.clear()
    st.rerun()

# Avvio scaricamento dati
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

    # 🟢 Generazione Opzione Cassaforte
    if p_1 > 60:
        cassa_label, cassa_q, cassa_p = "1X DOPPIA CHANCE", round(1 / ((p_1+p_X)/100), 2), min(98.0, p_1 + p_X)
    elif p_2 > 60:
        cassa_label, cassa_q, cassa_p = "X2 DOPPIA CHANCE", round(1 / ((p_2+p_X)/100), 2), min(98.0, p_2 + p_X)
    else:
        cassa_label, cassa_q, cassa_p = "OVER 1.5 GOL", 1.22, 83.5
    if cassa_q < 1.15: cassa_q = 1.20

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

    # Salviamo l'intero pacchetto dati del match
    database_completo.append({
        "coppia": f"{home_team} vs {away_team}",
        "lavagna": f"1: {quota_1} | X: {quota_X} | 2: {quota_2}",
        "cassa": {"giocata": cassa_label, "quota": cassa_q, "prob": cassa_p},
        "medio": {"giocata": medio_label, "quota": medio_q, "prob": medio_p},
        "alta": {"giocata": alta_label, "quota": alta_q, "prob": alta_p}
    })

# ==========================================
# 📊 SEZIONE IN PRIMO PIANO: LA SCHEDINA DINAMICA
# ==========================================
st.header("💰 La Tua Schedina Personalizzata")
st.caption("Modifica le impostazioni nella barra laterale sinistra per cambiare strategia!")

# Prepariamo la lista dei candidati in base alla strategia scelta dall'utente sul sito
candidati_filtrati = []
chiave_strategia = "cassa" if "🟢" in tipo_strategia else ("medio" if "🟡" in tipo_strategia else "alta")

for d in database_completo:
    candidati_filtrati.append({
        "match": d["coppia"],
        "giocata": d[chiave_strategia]["giocata"],
        "quota": d[chiave_strategia]["quota"],
        "prob": d[chiave_strategia]["prob"]
    })

# Ordina per probabilità di successo ed estrae il numero di eventi chiesto dall'utente
candidati_filtrati = sorted(candidati_filtrati, key=lambda x: x['prob'], reverse=True)
schedina_utente = candidati_filtrati[:num_eventi]

if len(schedina_utente) < 2:
    st.warning("⚠️ Troppi pochi eventi nel palinsesto attuale per soddisfare i filtri.")
else:
    quota_totale = 1.0
    # Box grafico per contenere la schedina del giorno
    with st.container():
        for i, part in enumerate(schedina_utente, 1):
            st.info(f"📌 **{i}. {part['match']}** \n\n Esito: `{part['giocata']}` | Quota: **{part['quota']:.2f}** (Affidabilità: {part['prob']:.1f}%)")
            quota_totale *= part['quota']
        
        st.success(f"🔥 **QUOTA TOTALE MOLTIPLICATORE: {quota_totale:.2f}**")

# ==========================================
# 📚 SEZIONE IN BASSO: LO STUDIO DETTAGLIATO MATCH PER MATCH
# ==========================================
st.markdown("---")
st.header("📚 Il Centro Studi dell'Algoritmo")
st.write("Clicca sulle singole partite qui sotto per vedere l'analisi matematica completa dei 3 livelli di rischio:")

for d in database_completo:
    with st.expander(f"🏟️ {d['coppia']}"):
        st.write(f"**Quote di Partenza dei Bookmaker:** `{d['lavagna']}`")
        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 CASSAFORTE", d["cassa"]["giocata"], f"{d['cassa']['quota']:.2f}")
        col2.metric("🟡 MEDIO", d["medio"]["giocata"], f"{d['medio']['quota']:.2f}")
        col3.metric("🔴 ALTA QUOTA", d["alta"]["giocata"], f"{d['alta']['quota']:.2f}")

# FOOTER DI COPYRIGHT
st.markdown("---")
st.caption("© 2026 Mondiali Advisor | Sviluppato e ingegnerizzato da Salvatore Cosmano. Tutti i diritti riservati.")
