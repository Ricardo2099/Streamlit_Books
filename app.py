import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Books Dashboard",
    page_icon="📚",
    layout="wide",
)


@st.cache_data
def load_books():
    """Carga el CSV local y prepara las columnas utilizadas en el análisis."""
    def repair_csv_row(row):
        # El dataset contiene una coma sin escapar en un autor concreto.
        if len(row) == 13:
            row[2] = f"{row[2]}, {row[3]}"
            del row[3]
        return row

    df = pd.read_csv(
        "books.csv",
        engine="python",
        on_bad_lines=repair_csv_row,
    )
    df.columns = df.columns.str.strip()

    required_columns = {
        "title",
        "authors",
        "average_rating",
        "language_code",
        "num_pages",
        "ratings_count",
        "publication_date",
        "publisher",
    }
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(
            "Faltan columnas requeridas en books.csv: "
            + ", ".join(sorted(missing_columns))
        )

    df["average_rating"] = pd.to_numeric(df["average_rating"], errors="coerce")
    df["num_pages"] = pd.to_numeric(df["num_pages"], errors="coerce")
    df["ratings_count"] = pd.to_numeric(df["ratings_count"], errors="coerce")
    df["publication_date"] = pd.to_datetime(
        df["publication_date"], errors="coerce"
    )
    return df


def format_number(value):
    return f"{value:,.0f}"


try:
    books = load_books()
except (FileNotFoundError, ValueError) as error:
    st.error(f"No se pudo cargar el dataset: {error}")
    st.stop()


def show_metrics(data):
    metric_columns = st.columns(4)
    average_rating = data["average_rating"].mean()
    average_pages = data["num_pages"].mean()
    total_ratings = data["ratings_count"].sum()
    metric_columns[0].metric("Libros", format_number(len(data)))
    metric_columns[1].metric(
        "Rating promedio", f"{average_rating:.2f}" if pd.notna(average_rating) else "N/D"
    )
    metric_columns[2].metric(
        "Promedio de páginas", f"{average_pages:,.0f}" if pd.notna(average_pages) else "N/D"
    )
    metric_columns[3].metric("Total de valoraciones", format_number(total_ratings))


def show_book_table(data, title=" Libros"):
    st.subheader(title)
    st.write(f"Mostrando {len(data):,} libros")
    table_columns = [
        "title", "authors", "average_rating", "num_pages",
        "ratings_count", "language_code", "publication_date", "publisher",
    ]
    st.dataframe(data[table_columns], use_container_width=True, hide_index=True)


st.title(" Books Dashboard")
st.write("Explora y analiza información sobre libros, calificaciones y publicaciones.")

with st.sidebar:
    st.header("Navegación")
    selected_view = st.radio(
        "Selecciona una vista",
        ["Resumen", "Explorador de libros", "Gráficas", "Rankings", "Publicaciones"],
    )
    st.divider()
    st.header("Filtros")
    languages = sorted(books["language_code"].dropna().unique().tolist())
    selected_languages = st.multiselect("Idioma", ["Todos"] + languages, ["Todos"])
    rating_values = books["average_rating"].dropna()
    rating_min = float(rating_values.min()) if not rating_values.empty else 0.0
    rating_max = float(rating_values.max()) if not rating_values.empty else 5.0
    rating_range = st.slider("Rango de rating", rating_min, rating_max, (rating_min, rating_max), 0.01)
    page_values = books["num_pages"].dropna()
    page_min = int(page_values.min()) if not page_values.empty else 0
    page_max = int(page_values.max()) if not page_values.empty else 0
    page_range = st.slider("Rango de páginas", page_min, page_max, (page_min, page_max))

filtered_books = books[
    books["average_rating"].between(*rating_range, inclusive="both")
    & books["num_pages"].between(*page_range, inclusive="both")
]
if selected_languages and "Todos" not in selected_languages:
    filtered_books = filtered_books[filtered_books["language_code"].isin(selected_languages)]

if filtered_books.empty:
    st.warning("No hay libros que coincidan con los filtros seleccionados.")
else:
    if selected_view == "Resumen":
        st.header("Resumen del catálogo")
        show_metrics(filtered_books)
        st.subheader("Idiomas con más libros")
        language_summary = filtered_books["language_code"].value_counts().head(10).rename("libros")
        st.bar_chart(language_summary, horizontal=True, use_container_width=True)
        st.caption("Usa el menú lateral para abrir cada análisis en una vista independiente.")

    elif selected_view == "Explorador de libros":
        st.header("Explorador de libros")
        search_text = st.text_input("Buscar por título o autor")
        searched_books = filtered_books
        if search_text:
            search_mask = (
                searched_books["title"].str.contains(search_text, case=False, na=False)
                | searched_books["authors"].str.contains(search_text, case=False, na=False)
            )
            searched_books = searched_books[search_mask]
        show_metrics(searched_books)
        show_book_table(searched_books)

    elif selected_view == "Gráficas":
        st.header("Gráficas del catálogo")
        chart_choice = st.selectbox(
            "Selecciona una gráfica",
            [
                "Distribución de calificaciones",
                "Páginas vs rating",
                "Rating promedio por idioma",
            ],
        )
        fig, ax = plt.subplots(figsize=(10, 5))
        if chart_choice == "Distribución de calificaciones":
            ax.hist(filtered_books["average_rating"].dropna(), bins=20, color="#2f6f8f", edgecolor="white")
            ax.set_xlabel("Calificación promedio")
            ax.set_ylabel("Cantidad de libros")
        elif chart_choice == "Páginas vs rating":
            chart_data = filtered_books.dropna(subset=["num_pages", "average_rating"])
            ax.scatter(chart_data["num_pages"], chart_data["average_rating"], alpha=0.3, color="#4c956c")
            ax.set_xlabel("Número de páginas")
            ax.set_ylabel("Calificación promedio")
        else:
            language_rating = (
                filtered_books.groupby("language_code")
                .agg(rating=("average_rating", "mean"), books=("average_rating", "count"))
                .query("books >= 10").nlargest(10, "rating").sort_values("rating")
            )
            ax.barh(language_rating.index, language_rating["rating"], color="#e09f3e")
            ax.set_xlabel("Rating promedio")
            ax.set_ylabel("Idioma")
        ax.set_title(chart_choice)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    elif selected_view == "Rankings":
        st.header("Rankings")
        ranking_choice = st.selectbox("Selecciona un ranking", ["Libros más valorados", "Idiomas con más libros"])
        if ranking_choice == "Libros más valorados":
            ranking = filtered_books.nlargest(10, "ratings_count")[
                ["title", "authors", "ratings_count", "average_rating"]
            ].reset_index(drop=True)
            st.subheader("Tabla: libros más valorados")
            st.dataframe(ranking, use_container_width=True, hide_index=True)
            st.subheader("Gráfica: libros más valorados")
            st.bar_chart(ranking.set_index("title")["ratings_count"], horizontal=True, use_container_width=True)
        else:
            language_ranking = filtered_books["language_code"].value_counts().head(10)
            st.subheader("Tabla: idiomas con más libros")
            st.dataframe(language_ranking.rename("libros"), use_container_width=True)
            st.subheader("Gráfica: idiomas con más libros")
            st.bar_chart(language_ranking, horizontal=True, use_container_width=True)

    else:
        st.header("Publicaciones por año")
        books_by_year = (
            filtered_books.dropna(subset=["publication_date"])
            .assign(year=lambda data: data["publication_date"].dt.year)
            .groupby("year").size().rename("libros")
        )
        st.subheader("Gráfica: libros publicados por año")
        st.line_chart(books_by_year, use_container_width=True)
        st.subheader("Tabla: libros publicados por año")
        publication_table = books_by_year.rename_axis("year").reset_index()
        st.dataframe(
            publication_table,
            width=360,
            hide_index=True,
            column_config={
                "year": st.column_config.NumberColumn("Año", width="small"),
                "libros": st.column_config.NumberColumn("Libros", width="small"),
            },
        )