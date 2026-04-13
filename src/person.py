from notion import _request, get_database_schema, find_by_name

def get_person_schema(db_id):
    """Devuelve el esquema de propiedades para la base de personas"""
    return get_database_schema(db_id)

def find_person_by_name(db_id, name, title_prop="Nombre"):
    """Busca una persona por nombre en la base de personas"""
    return find_by_name(db_id, name, title_prop)

def create_person_page(db_id, name, role=None, prop_map=None, image_url=None):
    """Crea una página de persona (actor/director) en Notion"""
    title_key = prop_map.get("Nombre")
    role_key = prop_map.get("Rol")
    image_key = prop_map.get("Foto")

    properties = {}
    if title_key:
        properties[title_key] = {"title": [{"text": {"content": name}}]}
    if role and role_key:
        properties[role_key] = {"select": {"name": role}}
    if image_url and image_key:
        properties[image_key] = {"files": [{"name": name, "external": {"url": image_url}}]}

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties
    }
    return _request("post", "pages", json=payload)

def build_person_relations(db_id, prop_map, people_list, role="Actor", max_count=5):
    """
    Recibe una lista de personas (cast o crew) y devuelve relaciones para Notion.
    Crea las páginas si no existen.
    """
    relations = []
    for person in people_list[:max_count]:
        name = person.get("name")
        person_id = person.get("id")
        if not name or not person_id:
            continue

        image_url = None
        if person.get("profile_path"):
            image_url = f"https://image.tmdb.org/t/p/original{person['profile_path']}"

        existing = find_person_by_name(db_id, name, title_prop=prop_map.get("Nombre"))
        if not existing:
            created = create_person_page(db_id, name, role, prop_map, image_url=image_url)
            if created:
                relations.append({"id": created["id"]})
        else:
            relations.append({"id": existing["id"]})
    return relations