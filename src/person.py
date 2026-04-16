from notion import _request, get_database_schema, find_by_name

# Centralizamos la base de imágenes para mantener consistencia con notion.py
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/original"

def get_person_schema(db_id):
    """Devuelve el esquema de propiedades para la base de personas."""
    return get_database_schema(db_id)

def find_person_by_name(db_id, name, title_prop="Nombre"):
    """Busca una persona por nombre en la base de personas."""
    return find_by_name(db_id, name, title_prop)

def create_person_page(db_id, name, role=None, prop_map=None, image_url=None):
    """Crea una página de persona (actor/director) en Notion."""
    p = prop_map or {}
    props = {}

    # Usamos el operador morsa (:=) para asignar y validar en una sola línea
    if key := p.get("Nombre"):
        props[key] = {"title": [{"text": {"content": name}}]}
    
    if role and (key := p.get("Rol")):
        props[key] = {"select": {"name": role}}
    
    if image_url and (key := p.get("Foto")):
        props[key] = {"files": [{"name": name, "external": {"url": image_url}}]}

    return _request("post", "pages", json={"parent": {"database_id": db_id}, "properties": props})

def build_person_relations(db_id, prop_map, people_list, role="Actor", max_count=5):
    """
    Orquesta la creación masiva de personas y devuelve la lista de IDs para la relación.
    """
    relations = []
    p_map = prop_map or {}
    nombre_col = p_map.get("Nombre", "Nombre")

    for person in people_list[:max_count]:
        name = person.get("name")
        if not name:
            continue

        # 1. Verificamos si ya existe para evitar duplicados
        existing = find_person_by_name(db_id, name, title_prop=nombre_col)
        
        if existing:
            relations.append({"id": existing["id"]})
            continue # Saltamos a la siguiente persona si esta ya está

        # 2. Si no existe, preparamos la info y la creamos
        path = person.get("profile_path")
        image_url = f"{TMDB_IMG_BASE}{path}" if path else None
        
        created = create_person_page(db_id, name, role, p_map, image_url)
        if created:
            relations.append({"id": created["id"]})
            
    return relations