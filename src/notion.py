import requests
from config import NOTION_TOKEN

BASE_URL = "https://api.notion.com/v1/"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/original"

def _request(method, endpoint, json=None):
    """Motor central de peticiones para Notion."""
    url = f"{BASE_URL}{endpoint}"
    try:
        res = requests.request(method, url, headers=HEADERS, json=json)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"❌ Error en Notion API [{method.upper()} {endpoint}]: {e}")
        return None

def get_pages(db_id):
    """Recupera todos los registros manejando la paginación de Notion."""
    all_pages = []
    payload = {}
    while True:
        data = _request("post", f"databases/{db_id}/query", json=payload)
        if not data: break
        
        all_pages.extend(data.get("results", []))
        
        if data.get("has_more"):
            payload["start_cursor"] = data.get("next_cursor")
        else:
            break
    return all_pages

def update_page(page_id, properties):
    """Actualiza propiedades de una página existente."""
    return _request("patch", f"pages/{page_id}", json={"properties": properties})

def get_database_schema(db_id):
    """Mapea nombres de columnas con sus IDs internos."""
    data = _request("get", f"databases/{db_id}")
    if not data: return {}
    return {v["name"]: k for k, v in data["properties"].items()}

def find_by_name(db_id, name, title_prop="Titulo"):
    """Busca una página por su título para evitar duplicados."""
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
    """Crea una página en la base de datos de Sagas/Colecciones."""
    p = prop_map or {}
    properties = {
        p.get("Titulo", "Titulo"): {"title": [{"text": {"content": name}}]}
    }
    
    if description and p.get("Descripcion"):
        properties[p["Descripcion"]] = {"rich_text": [{"text": {"content": description}}]}
    
    if poster_url and p.get("Poster"):
        properties[p["Poster"]] = {"files": [{"name": "Poster", "external": {"url": poster_url}}]}

    return _request("post", "pages", json={"parent": {"database_id": db_id}, "properties": properties})

def create_movie_page(db_id, movie_data, prop_map, saga_page=None, genres_dict=None, extra_properties=None):
    """Construye el payload complejo para insertar una película."""
    # Extracción limpia de datos
    title = movie_data.get("title") or movie_data.get("name") or "Sin título"
    date_str = movie_data.get("release_date", "")
    overview = movie_data.get("overview")
    poster_path = movie_data.get("poster_path")
    genre_ids = movie_data.get("genre_ids", [])

    props = {}
    
    # Mapeo dinámico usando f-strings y validaciones cortas
    if key := prop_map.get("Titulo"):
        props[key] = {"title": [{"text": {"content": title}}]}
        
    if key := prop_map.get("Estado"):
        props[key] = {"select": {"name": "Vista"}}
        
    if (key := prop_map.get("Año")) and date_str:
        props[key] = {"number": int(date_str.split("-")[0])}
        
    if (key := prop_map.get("Descripcion")) and overview:
        props[key] = {"rich_text": [{"text": {"content": overview}}]}
        
    if (key := prop_map.get("Poster")) and poster_path:
        props[key] = {"files": [{"name": title, "external": {"url": f"{TMDB_IMG_BASE}{poster_path}"}}]}
        
    if (key := prop_map.get("Generos")) and genres_dict:
        names = [genres_dict[gid] for gid in genre_ids if gid in genres_dict]
        if names:
            props[key] = {"multi_select": [{"name": n} for n in names]}
            
    if (key := prop_map.get("Saga")) and saga_page:
        props[key] = {"relation": [{"id": saga_page["id"]}]}

    if extra_properties:
        props.update(extra_properties)

    return _request("post", "pages", json={"parent": {"database_id": db_id}, "properties": props})