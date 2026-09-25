import datetime as dt
from contextlib import closing

import pandas as pd
import pyodbc
import streamlit as st


st.set_page_config(page_title="Super Brayan", page_icon="📋", layout="wide")
st.title("Registros de Super Brayan")


def get_setting(name: str) -> str:
    try:
        value = st.secrets["sqlserver"][name]
    except (KeyError, TypeError):
        st.error(
            "Faltan Secrets de SQL Server. Configura la sección [sqlserver] "
            "en .streamlit/secrets.toml localmente o en la configuración de "
            "Secrets de Streamlit Cloud."
        )
        st.stop()

    if not value:
        st.error(f"El Secret '{name}' está vacío.")
        st.stop()

    return str(value)


def get_connection_string() -> str:
    available_drivers = pyodbc.drivers()
    driver = next(
        (
            candidate
            for candidate in (
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
                "SQL Server",
            )
            if candidate in available_drivers
        ),
        None,
    )

    if driver is None:
        raise RuntimeError(
            "No se encontró un driver ODBC compatible. Drivers disponibles: "
            + (", ".join(available_drivers) if available_drivers else "ninguno")
        )

    return (
        f"Driver={{{driver}}};"
        f"Server={get_setting('server')};"
        f"Database={get_setting('database')};"
        f"UID={get_setting('username')};"
        f"PWD={get_setting('password')};"
        "MARS_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


def load_records() -> pd.DataFrame:
    connection_string = get_connection_string()
    query = """
        SELECT [Nombre], [Fecha], [hora]
        FROM dbo.Super_Brayan
        ORDER BY [Fecha] DESC, [hora] DESC
    """
    with closing(pyodbc.connect(connection_string)) as connection:
        return pd.read_sql_query(query, connection)


def insert_record(nombre: str, fecha: dt.date, hora: dt.time) -> None:
    connection_string = get_connection_string()
    query = """
        INSERT INTO dbo.Super_Brayan ([Nombre], [Fecha], [hora])
        VALUES (?, ?, ?)
    """
    with closing(pyodbc.connect(connection_string)) as connection:
        cursor = connection.cursor()
        cursor.execute(query, nombre, fecha, hora)
        connection.commit()


tab_view, tab_add = st.tabs(["Ver registros", "Agregar registro"])

with tab_view:
    st.subheader("Registros guardados")
    if st.button("Actualizar", key="refresh_records"):
        st.rerun()

    try:
        records = load_records()
        st.dataframe(records, width="stretch", hide_index=True)
        st.caption(f"Total de registros: {len(records)}")
    except Exception as error:
        st.error(f"No se pudieron cargar los registros: {error}")

with tab_add:
    st.subheader("Agregar un registro")
    with st.form("add_record_form", clear_on_submit=True):
        nombre = st.text_input("Nombre", max_chars=200)
        fecha = st.date_input("Fecha", value=dt.date.today())
        hora = st.time_input("Hora", value=dt.datetime.now().time().replace(second=0, microsecond=0))
        submitted = st.form_submit_button("Guardar registro")

    if submitted:
        clean_nombre = nombre.strip()
        if not clean_nombre:
            st.warning("Escribe un nombre antes de guardar.")
        else:
            try:
                insert_record(clean_nombre, fecha, hora)
                st.success("El registro se guardó correctamente.")
            except Exception as error:
                st.error(f"No se pudo guardar el registro: {error}")
