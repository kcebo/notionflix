import requests
from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"

def _get(endpoint, params=None):
    """Función auxiliar para hacer GET a TMDB con manejo de errores"""
    url = f"{BASE_URL}/{endpoint}"
    params = params or {}
    params["api_key"] = TMDB_API_KEY
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"❌ Error al consultar TMDB: {e}")
        return None

def search_movie(title, year=None, max_results=5, interactive=True):
    """Busca una película por título (y opcionalmente año)"""
    params = {"query": title, "language": "en-US"}
    if year:
        params["year"] = year

    data = _get("search/movie", params)
    if not data:
        return None

    results = data.get("results", [])
    if not results:
        print(f"⚠️ No se encontraron resultados para: {title}")
        return None

    if len(results) == 1 or not interactive:
        return results[0]

    print(f"\n🔍 Se encontraron varias opciones para: {title}")
    for idx, movie in enumerate(results[:max_results], start=1):
        title_res = movie.get("title")
        year_res = movie.get("release_date", "????")[:4]
        overview = movie.get("overview", "")
        print(f"{idx}. {title_res} ({year_res}) - {overview[:80]}...")

    choice = input(f"Elige el número correcto (1-{min(max_results,len(results))}) o Enter para la primera opción: ")
    try:
        choice = int(choice)
        if 1 <= choice <= min(max_results, len(results)):
            return results[choice - 1]
    except ValueError:
        pass

    return results[0]

def get_genres():
    """Devuelve un diccionario {id: nombre} de géneros"""
    data = _get("genre/movie/list", {"language": "es-ES"})
    return {g["id"]: g["name"] for g in data.get("genres", [])} if data else {}

def get_movie(movie_id):
    """Devuelve los datos completos de una película por ID"""
    return _get(f"movie/{movie_id}", {"language": "en-US"})

def get_collection(collection_id):
    """Devuelve los datos de una colección (saga) por ID"""
    return _get(f"collection/{collection_id}", {"language": "en-uS"})

def get_credits(movie_id):
    """Devuelve los créditos (cast y crew) de una película"""
    return _get(f"movie/{movie_id}/credits", {"language": "en-US"})

def get_person(person_id):
    """Devuelve los datos completos de una persona (actor/director)"""
    return _get(f"person/{person_id}", {"language": "en-uS"})