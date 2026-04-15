import requests
from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"
DEFAULT_LANG = "en-US" # Centralizamos el idioma aquí

def _get(endpoint, params=None):
    """Función auxiliar para hacer GET a TMDB con manejo de errores."""
    url = f"{BASE_URL}/{endpoint}"
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"❌ Error al consultar TMDB ({endpoint}): {e}")
        return None

def search_movie(title, year=None, max_results=5, interactive=True):
    """Busca una película por título y maneja la selección del usuario."""
    params = {"query": title, "language": DEFAULT_LANG}
    if year:
        params["year"] = year

    data = _get("search/movie", params)
    if not data or not data.get("results"):
        print(f"⚠️ No se encontraron resultados para: {title}")
        return None

    results = data["results"]

    # Si solo hay uno o no es interactivo, devolvemos el primero
    if len(results) == 1 or not interactive:
        return results[0]

    # Lógica de selección interactiva mejorada
    print(f"\n🔍 Varias opciones para: '{title}'")
    limite = min(max_results, len(results))
    
    for i in range(limite):
        m = results[i]
        t = m.get("title", "Sin título")
        y = m.get("release_date", "????")[:4]
        d = m.get("overview", "Sin descripción")[:80]
        print(f"{i + 1}. {t} ({y}) - {d}...")

    choice = input(f"Elige (1-{limite}) o Enter para el 1ero: ").strip()
    
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < limite:
            return results[idx]
            
    return results[0]

def get_genres():
    """Devuelve un diccionario {id: nombre} de géneros."""
    data = _get("genre/movie/list", {"language": DEFAULT_LANG})
    return {g["id"]: g["name"] for g in data.get("genres", [])} if data else {}

def get_movie(movie_id):
    """Devuelve los datos detallados de una película."""
    return _get(f"movie/{movie_id}", {"language": DEFAULT_LANG})

def get_collection(collection_id):
    """Obtiene datos de una saga (ej. Star Wars)."""
    return _get(f"collection/{collection_id}", {"language": DEFAULT_LANG})

def get_credits(movie_id):
    """Obtiene el reparto y equipo técnico."""
    return _get(f"movie/{movie_id}/credits", {"language": DEFAULT_LANG})