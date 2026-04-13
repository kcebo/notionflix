import requests
from config import NOTION_TOKEN

BASE_URL = "https://api.notion.com/v1/"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def _request(method, endpoint, json=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        res = requests.request(method, url, headers=HEADERS, json=json)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"❌ Error en Notion API: {e}")
        return None

def get_pages(db_id):
    """Devuelve todas las páginas de una base de datos"""
    all_pages = []
    payload = {}
    while True:
        data = _request("post", f"databases/{db_id}/query", json=payload)
        if not data:
            break
        all_pages.extend(data.get("results", []))
        if data.get("has_more"):
            payload["start_cursor"] = data.get("next_cursor")
        else:
            break
    return all_pages

def update_page(page_id, properties):
    """Actualiza propiedades de una página"""
    return _request("patch", f"pages/{page_id}", json={"properties": properties})

def get_database_schema(db_id):
    """Devuelve {nombre_propiedad: id_propiedad} para una base"""
    data = _request("get", f"databases/{db_id}")
    if not data:
        return {}
    return {v["name"]: k for k, v in data["properties"].items()}

def find_by_name(db_id, name, title_prop="Titulo"):
    """Busca una página por nombre en una base específica"""
    payload = {
        "filter": {
            "property": title_prop,
            "title": {"equals": name}
        }
    }
    data = _request("post", f"databases/{db_id}/query", json=payload)
    results = data.get("results", []) if data else []
    return results[0] if results else None

def create_collection_page(db_id, name, description=None, poster_url=None, prop_map=None):
    """Crea una página de colección"""
    title_key = prop_map.get("Titulo") if prop_map else "Titulo"
    desc_key = prop_map.get("Descripcion") if prop_map else "Descripcion"
    poster_key = prop_map.get("Poster") if prop_map else "Poster"

    properties = {
        title_key: {"title": [{"text": {"content": name}}]}
    }
    if description and desc_key:
        properties[desc_key] = {"rich_text": [{"text": {"content": description}}]}
    if poster_url and poster_key:
        properties[poster_key] = {"files": [{"name": "poster", "external": {"url": poster_url}}]}

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties
    }
    return _request("post", "pages", json=payload)

def create_movie_page(db_id, movie_data, prop_map, saga_page=None, genres_dict=None, extra_properties=None):
    title = movie_data.get("title") or movie_data.get("name") or "Sin título"
    release_date = movie_data.get("release_date")
    overview = movie_data.get("overview")
    poster_path = movie_data.get("poster_path")
    genre_ids = movie_data.get("genre_ids", [])

    properties = {}

    if prop_map.get("Titulo"):
        properties[prop_map["Titulo"]] = {"title": [{"text": {"content": title}}]}
    if prop_map.get("Estado"):
        properties[prop_map["Estado"]] = {"select": {"name": "Vista"}}
    if prop_map.get("Año") and release_date:
        try:
            properties[prop_map["Año"]] = {"number": int(release_date.split("-")[0])}
        except ValueError:
            pass
    if prop_map.get("Descripcion") and overview:
        properties[prop_map["Descripcion"]] = {"rich_text": [{"text": {"content": overview}}]}
    if prop_map.get("Poster") and poster_path:
        poster_url = f"https://image.tmdb.org/t/p/original{poster_path}"
        properties[prop_map["Poster"]] = {"files": [{"name": title, "external": {"url": poster_url}}]}
    if prop_map.get("Generos") and genre_ids and genres_dict:
        valid_genres = [genres_dict.get(gid) for gid in genre_ids if genres_dict.get(gid)]
        if valid_genres:
            properties[prop_map["Generos"]] = {"multi_select": [{"name": g} for g in valid_genres]}
    if saga_page and prop_map.get("Saga"):
        properties[prop_map["Saga"]] = {"relation": [{"id": saga_page["id"]}]}

    # 🔗 Agregar relaciones extra (como Elenco)
    if extra_properties:
        properties.update(extra_properties)

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties
    }
    return _request("post", "pages", json=payload)