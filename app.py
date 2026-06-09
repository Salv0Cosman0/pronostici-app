import streamlit as pd
import streamlit as st
import requests
import numpy as np

# Configurazione grafica della pagina
st.set_page_config(page_title="Mondiali Advisor - Schedine Live", page_icon="⚽", layout="centered")

st.title("⚽ Mondiali Advisor")
st.subheader("I pronostici matematici in tempo reale per la tua bolletta")
st.markdown("---")

# Recupero automatico e sicuro della chiave API nascosta nei Secrets
try:
    API_KEY = st.secrets["THE_ODDS_API_KEY"]
except Exception:
    st.error("❌ Errore di configurazione: Chiave API non trovata nei Secrets del server.")
    st.stop()

REGIO = "eu"          
MARKETS = "h2h,totals" 

@st.cache_data(ttl=3600)  # Salva i dati in cache per 1 ora per non consumare i crediti gratis dell'API
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

# Avvio scaricamento dati
with st.spinner("🔄 Connessione ai bookmaker e analisi del palinsesto in corso..."):
    oracoli_data = scarica_dati_live()

if not oracoli_data or 'error' in oracoli_data:
    st.error("Impossibile caricare i palinsesti in questo momento. Riprova più tardi.")
    st.stop()

candidati_schedina = []

st.header("📚 Lo Studio delle Partite")

# Ciclo analisi dei match
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

    # Logica 3 Livelli Pronostici
    if p_1 > 60:
        cassaforte = "1X DOPPIA CHANCE"
        prob_cassa = min(98.0, p_1 + p_X)
    elif p_2 > 60:
        cassaforte = "X2 DOPPIA CHANCE"
        prob_cassa = min(98.0, p_2 + p_X)
    else:
        cassaforte = "OVER 1.5 GOL"
        prob_cassa = 83.5

    if p_1 > p_2 and p_1 > 45:
        medio = "1 FISSO"
        prob_medio = p_1
    elif p_2 > p_1 and p_2 > 45:
        medio = "2 FISSO"
        prob_medio = p_2
    else:
        medio = "UNDER 3.5 GOL"
        prob_medio = 70.0

    if quota_over and quota_over < 2.10:
        alta_quota = "OVER 2.5 GOL"
        prob_alta = (1 / quota_over) * 100
    else:
        alta_quota = "ESITO PAREGGIO (X)"
        prob_alta = p_X

    # Mostra lo studio del match in un box grafico espandibile per ogni partita
    with st.expander(f"🏟️ {home_team} vs {away_team}"):
        st.write(f"**Lavagna Quote Bookmaker:** 1 ({quota_1}) | X ({quota_X}) | 2 ({quota_2})")
        col1, col2, col3 = st.columns(3)
        col1.metric("🟢 CASSAFORTE", cassaforte, f"{prob_cassa:.1f}%")
        col2.metric("🟡 MEDIO", medio, f"{prob_medio:.1f}%")
        col3.metric("🔴 ALTA QUOTA", alta_quota, f"{prob_alta:.1f}%")

    # Selezione per schedina finale
    if 1.28 <= quota_1 <= 1.70:
        candidati_schedina.append({"match": f"{home_team} vs {away_team}", "giocata": "1 FISSO", "quota": quota_1, "prob": p_1})
    elif 1.28 <= quota_2 <= 1.70:
        candidati_schedina.append({"match": f"{home_team} vs {away_team}", "giocata": "2 FISSO", "quota": quota_2, "prob": p_2})
    elif quota_over and 1.35 <= quota_over <= 1.70:
        candidati_schedina.append({"match": f"{home_team} vs {away_team}", "giocata": "OVER 2.5 GOL", "quota": quota_over, "prob": (1/quota_over)*100})

# Costruzione Schedina Finale in fondo alla pagina
st.markdown("---")
st.header("💰 La Schedina Consigliata dall'Algoritmo")

candidati_schedina = sorted(candidati_schedina, key=lambda x: x['prob'], reverse=True)
schedina_pulita = candidati_schedina[:3]

if len(schedina_pulita) < 2:
    st.warning("⚠️ Palinsesto troppo instabile oggi per generare una bolletta sicura. Consulta i singoli studi qui sopra!")
else:
    quota_totale = 1.0
    for i, part in enumerate(schedina_pulita, 1):
        st.info(f"**{i}. {part['match']}** \n\n  👉 Giocata: `{part['giocata']}` | 📉 Quota: **{part['quota']:.2f}** (Affidabilità: {part['prob']:.1f}%)")
        quota_totale *= part['quota']
    
    st.success(f"🔥 **QUOTA TOTALE DELLA BOLLETTA: {quota_totale:.2f}**")