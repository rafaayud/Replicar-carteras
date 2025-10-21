# app.py
import streamlit as st
import pandas as pd
from diccionario_inversores import get_superinvestor_updates
from cartera2 import Wallet
import sqlite3, uuid, time

st.set_page_config(page_title="Replicar carteras", layout="wide")
st.title("Replicar carteras de grandes inversores")

def load_investors() -> dict:
    d = get_superinvestor_updates()
    # normaliza URLs móviles a escritorio
    # d = {k: v.replace("://www.dataroma.com/m/", "://www.dataroma.com/", 1) for k, v in d.items()}
    return d

# def load_holdings(name_investor: str, dic: dict) -> pd.DataFrame:
#     # sc.diccionario_inversores = dic  # por compatibilidad con tu get_tables
#     return get_tables(name_investor)
def get_conn():
    conn = sqlite3.connect("replicar.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      username TEXT UNIQUE NOT NULL,
      created_at REAL NOT NULL
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      investor TEXT NOT NULL,
      amount REAL NOT NULL,
      portfolio_date TEXT,
      created_at REAL NOT NULL,
      df_json TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    return conn

def get_or_create_user(conn, username: str) -> str:
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if row:
        return row[0]
    uid = str(uuid.uuid4())
    cur.execute("INSERT INTO users(id, username, created_at) VALUES(?,?,?)",
                (uid, username, time.time()))
    conn.commit()
    return uid

def save_portfolio(conn, user_id: str, investor: str, amount: float, portfolio_date, df_wallet: pd.DataFrame) -> str:
    pid = str(uuid.uuid4())
    df_json = df_wallet.to_json(orient="records")
    conn.execute(
        "INSERT INTO portfolios(id, user_id, investor, amount, portfolio_date, created_at, df_json) VALUES (?,?,?,?,?,?,?)",
        (pid, user_id, investor, amount,
         (portfolio_date.isoformat() if portfolio_date is not None else None),
         time.time(), df_json)
    )
    conn.commit()
    return pid

def list_user_portfolios(conn, user_id: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT id, investor, amount, portfolio_date, created_at FROM portfolios WHERE user_id=? ORDER BY created_at DESC",
        conn, params=(user_id,)
    )
    df["created_at"] = pd.to_datetime(df["created_at"], unit="s")
    return df

def load_portfolio_df(conn, portfolio_id: str, dicc: dict) -> pd.DataFrame | None:
    row = conn.execute(
        "SELECT investor, amount, portfolio_date, df_json FROM portfolios WHERE id=?",
        (portfolio_id,)
    ).fetchone()
    if not row:
        return None

    investor, amount, portfolio_date, df_json = row
    link = dicc.get(investor)

    if not link:
        raise KeyError(f"No tengo link para el inversor '{investor}'")

    w = Wallet(investor, link, amount)
    w.df_wallet = pd.read_json(df_json)
    final = w.show_wallet()
    return final
















# --- UI ---
dic = load_investors()

st.sidebar.header("Tu sesión")
conn = get_conn()

username = st.sidebar.text_input("Tu nombre o alias")
if st.sidebar.button("Entrar", key="btn_login"):
    if not username.strip():
        st.sidebar.warning("Escribe un alias.")
    else:
        st.session_state.user_id = get_or_create_user(conn, username.strip())
        st.session_state.username = username.strip()       # opcional
        st.sidebar.success(f"¡Hola, {username.strip()}!")

# Selector siempre visible
inv = st.selectbox("Elige inversor", list(dic.keys()))
amount = st.number_input("Cantidad a invertir ($)", min_value=0.0, value=10000.0, step=100.0)

# 1) Generar cartera → guardar snapshot en session_state
if st.button("Obtener holdings y replicar", type="primary", key="btn_fetch"):
    w = Wallet(inv, dic[inv], amount)
    w.create_wallet()
    df_wallet = w.show_wallet()
    # guardamos un snapshot para sobrevivir al siguiente rerun
    st.session_state.current_wallet = {
        "investor": inv,
        "amount": float(amount),
        "date": (w.date.isoformat() if w.date is not None else None),
        "df_json": w.df_wallet.to_json(orient="records")
    }

# 2) Mostrar la cartera actual si existe en session_state (aunque haya un rerun)
if "current_wallet" in st.session_state:
    snap = st.session_state.current_wallet
    df_wallet = pd.read_json(snap["df_json"])

    st.subheader(f"Cartera replicada · {snap['investor']} · ${snap['amount']:.2f}")
    if snap["date"]:
        st.caption(f"Portfolio date: {pd.to_datetime(snap['date']).date()}")

    st.dataframe(df_wallet, use_container_width=True)

    # 3) Botón de guardar SIEMPRE disponible cuando hay cartera cargada
    if "user_id" in st.session_state:
        if st.button("💾 Guardar esta cartera", key="btn_save"):
            pid = save_portfolio(
                conn,
                st.session_state.user_id,
                snap["investor"],
                snap["amount"],
                (pd.to_datetime(snap["date"]) if snap["date"] else None),
                df_wallet
            )
            st.success(f"Cartera guardada (id: {pid[:8]}…)")

# 4) Mostrar SIEMPRE el histórico del usuario al estar identificado
if "user_id" in st.session_state:
    st.subheader("Mis carteras guardadas")
    saved = list_user_portfolios(conn, st.session_state.user_id)
    if len(saved):
        st.dataframe(saved, use_container_width=True)
        sel = st.selectbox(
            "Ver cartera guardada",
            options=saved["id"].tolist(),
            format_func=lambda i: f"{saved.loc[saved['id']==i, 'investor'].values[0]} - "
                                  f"{saved.loc[saved['id']==i, 'created_at'].dt.strftime('%Y-%m-%d %H:%M').values[0]}",
            key="sel_saved"
        )
        if sel:
            df_saved = load_portfolio_df(conn, sel, dic)
            st.caption("Contenido de la cartera guardada")
            st.dataframe(df_saved, use_container_width=True)
            st.download_button(
                "Descargar cartera guardada (CSV)",
                df_saved.to_csv(index=False).encode("utf-8"),
                file_name=f"cartera_{sel[:8]}.csv",
                mime="text/csv",
                key="dl_saved_csv"
            )
    else:
        st.info("Aún no tienes carteras guardadas.")
else:
    st.info("Inicia sesión con un alias en la barra lateral para poder guardar y ver tus carteras.")
