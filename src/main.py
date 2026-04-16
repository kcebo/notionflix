from notion import (
    get_pages, get_database_schema, update_page,
    find_by_name, create_collection_page, create_movie_page
)
from tmdb import (
    search_movie, get_genres, get_movie,
    get_collection, get_credits
)
from person import (
    get_person_schema, build_person_relations
)
from config import MOVIE_DB_ID, COLLECTION_DB_ID, PERSON_DB_ID

def extract_title(page):
    """Extrae el título de una página de película de forma segura."""
    props = page.get("properties", {}).values()
    title_prop = next((p for p in props if p["type"] == "title"), None)
    if title_prop and title_prop["title"]:
        return title_prop["title"][0]["text"]["content"]
    return None

def has_poster(page, prop_map):
    """Verifica si la página ya tiene imagen de póster para evitar retrabajo."""
    poster_key = prop_map.get("Poster")
    poster_prop = page["properties"].get(poster_key)
    return poster_prop and poster_prop.get("files")

def handle_collection(movie, prop_map, genre_dict, created_movies, created_collections, person_map, created_people):
    """Maneja la lógica de sagas y crea las películas que faltan automáticamente."""
    movie_full = get_movie(movie["id"])
    col_info = movie_full.get("belongs_to_collection")
    if not col_info:
        return None

    col_name = col_info["name"]
    col_data = get_collection(col_info["id"])
    col_page = find_by_name(COLLECTION_DB_ID, col_name)
    
    if not col_page:
        path = col_data.get("poster_path")
        poster = f"https://image.tmdb.org/t/p/original{path}" if path else None
        col_page = create_collection_page(COLLECTION_DB_ID, col_name, col_data.get("overview"), poster, prop_map)
        if col_page:
            created_collections.append(col_name)

    for part in col_data.get("parts", []):
        if part["id"] == movie["id"] or find_by_name(MOVIE_DB_ID, part.get("title")):
            continue

        credits = get_credits(part["id"])
        crew = credits.get("crew", [])
        cast = credits.get("cast", [])
        director = next((p for p in crew if p.get("job") == "Director"), None)
        
        # Separación de roles para las películas de la saga
        a_ids = build_person_relations(PERSON_DB_ID, person_map, cast[:1], role="Actor")
        d_ids = build_person_relations(PERSON_DB_ID, person_map, [director] if director else [], role="Director")
        rel_ids = a_ids + d_ids

        # Trackeo de nombres para el resumen
        for p in [cast[0] if cast else None, director]:
            if p and p.get("name") and p["name"] not in created_people:
                created_people.append(p["name"])

        elenco_key = prop_map.get("Elenco")
        extra = {elenco_key: {"relation": rel_ids}} if elenco_key and rel_ids else {}

        if create_movie_page(MOVIE_DB_ID, part, prop_map, col_page, genre_dict, extra):
            created_movies.append(part.get("title"))
    
    return {"relation": [{"id": col_page["id"]}]} if col_page else None

def mostrar_resumen(actualizadas, omitidas, fallidas, creadas, colecciones, personas):
    """Tu función de resumen interactivo original."""
    print(f"\n📊 Resumen final:")
    print(f"  🎬 Películas creadas: {len(creadas)}")
    print(f"  📦 Colecciones creadas: {len(colecciones)}")
    print(f"  👤 Personas procesadas: {len(personas)}")
    print(f"  ✅ Actualizadas: {len(actualizadas)}")
    print(f"  ⏩ Omitidas: {len(omitidas)}")
    print(f"  ❌ Fallidas: {len(fallidas)}")

    if input("\n¿Desea ver el detalle de cada grupo? (s/n): ").strip().lower() == "s":
        if creadas:
            print("\n🎬 Películas creadas:"); [print(f"  🎬 {t}") for t in sorted(creadas)]
        if colecciones:
            print("\n📦 Colecciones creadas:"); [print(f"  📦 {c}") for c in sorted(colecciones)]
        if personas:
            print("\n👤 Personas procesadas:"); [print(f"  👤 {p}") for p in sorted(personas)]
        if actualizadas:
            print("\n✅ Películas actualizadas:"); [print(f"  ✅ {t}") for t in sorted(actualizadas)]
        if fallidas:
            print("\n❌ Películas no encontradas:"); [print(f"  ❌ {t}") for t in sorted(fallidas)]
    
    if input("\n¿Desea ver las que se omitieron? (s/n): ").strip().lower() == 's' and omitidas:
        print("\n⏩ Películas omitidas (ya tenían poster):")
        for t in sorted(omitidas): print(f"  ⏩ {t}")

def main():
    print("\n🚀 Iniciando NotionFlix...\n")
    upd, skip, fail, mov, col, pep = [], [], [], [], [], []

    prop_map = get_database_schema(MOVIE_DB_ID)
    genre_dict = get_genres()
    person_map = get_person_schema(PERSON_DB_ID)
    pages = get_pages(MOVIE_DB_ID)

    for page in pages:
        title = extract_title(page)
        if not title: continue
        
        if has_poster(page, prop_map):
            skip.append(title)
            continue

        print(f"🎬 Procesando: {title}")
        año_num = page["properties"].get(prop_map.get("Año"), {}).get("number")
        movie = search_movie(title, year=año_num, interactive=True)
        
        if not movie:
            fail.append(title)
            continue

        # 1. Gestionar Sagas y películas automáticas
        saga_rel = handle_collection(movie, prop_map, genre_dict, mov, col, person_map, pep)
        
        # 2. Gestionar Personas de la película actual (Corregido: Roles separados)
        credits = get_credits(movie["id"])
        cast = credits.get("cast", [])
        crew = credits.get("crew", [])
        director = next((p for p in crew if p.get("job") == "Director"), None)
        
        actor_ids = build_person_relations(PERSON_DB_ID, person_map, cast[:1], role="Actor")
        director_ids = build_person_relations(PERSON_DB_ID, person_map, [director] if director else [], role="Director")
        actor_dir_ids = actor_ids + director_ids

        for p in [cast[0] if cast else None, director]:
            if p and p.get("name") and p["name"] not in pep: pep.append(p["name"])

        # 3. Armar el update de propiedades (Corregido: Incluye Géneros)
        path = movie.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/original{path}" if path else ""
        
        props = {}
        if k := prop_map.get("Titulo"): props[k] = {"title": [{"text": {"content": movie.get("title", title)}}]}
        if (k := prop_map.get("Año")) and movie.get("release_date"): 
            props[k] = {"number": int(movie["release_date"].split("-")[0])}
        if (k := prop_map.get("Descripcion")) and movie.get("overview"): 
            props[k] = {"rich_text": [{"text": {"content": movie["overview"]}}]}
        if (k := prop_map.get("Poster")) and poster_url: 
            props[k] = {"files": [{"name": title, "external": {"url": poster_url}}]}
        
        # Bloque de Géneros para película base
        genre_ids = movie.get("genre_ids", [])
        if (k := prop_map.get("Generos")) and genre_ids:
            nombres = [genre_dict.get(gid) for gid in genre_ids if genre_dict.get(gid)]
            if nombres: props[k] = {"multi_select": [{"name": n} for n in nombres]}

        if (k := prop_map.get("Saga")) and saga_rel: props[k] = saga_rel
        if (k := prop_map.get("Elenco")) and actor_dir_ids: props[k] = {"relation": actor_dir_ids}

        if update_page(page["id"], props):
            upd.append(title)
            print(f"✅ '{title}' sincronizada.")

    mostrar_resumen(upd, skip, fail, mov, col, pep)
    print("\n🏁 Vuelva pronto! -- NotionFlix\n")

if __name__ == "__main__":
    main()