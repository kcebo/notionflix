from notion import (
    get_pages, get_database_schema, update_page,
    find_by_name, create_collection_page, create_movie_page
)
from tmdb import (
    search_movie, get_genres, get_movie,
    get_collection, get_credits, get_person
)
from person import (
    get_person_schema, find_person_by_name, create_person_page
)
from config import MOVIE_DB_ID, COLLECTION_DB_ID, PERSON_DB_ID

def extract_title(page):
    """Extrae el título de una página de película"""
    title_prop = next((v for v in page["properties"].values() if "title" in v), None)
    if title_prop and title_prop["title"]:
        return title_prop["title"][0]["text"]["content"]
    return None

def has_poster(page, prop_map):
    """Verifica si la página ya tiene imagen de póster"""
    poster_key = prop_map.get("Poster")
    poster_prop = page["properties"].get(poster_key)
    return poster_prop and poster_prop.get("files")

def build_properties(movie, title, prop_map, genre_dict):
    """Construye las propiedades para actualizar una película en Notion"""
    release_date = movie.get("release_date")
    overview = movie.get("overview") or ""
    poster_path = movie.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/original{poster_path}" if poster_path else ""
    genres = [genre_dict.get(gid) for gid in movie.get("genre_ids", []) if genre_dict.get(gid)]

    props = {}
    if prop_map.get("Titulo"):
        props[prop_map["Titulo"]] = {"title": [{"text": {"content": movie["original_title"]}}]}
    if release_date and prop_map.get("Año"):
        props[prop_map["Año"]] = {"number": int(release_date.split("-")[0])}
    if overview and prop_map.get("Descripcion"):
        props[prop_map["Descripcion"]] = {"rich_text": [{"text": {"content": overview}}]}
    if poster_url and prop_map.get("Poster"):
        props[prop_map["Poster"]] = {
            "files": [{"name": title, "external": {"url": poster_url}}]
        }
    if genres and prop_map.get("Generos"):
        props[prop_map["Generos"]] = {"multi_select": [{"name": g} for g in genres if g]}
    return props

def handle_collection(movie, prop_map, genre_dict, created_movies, created_collections,person_prop_map):
    saga_key = prop_map.get("Saga")
    elenco_key = prop_map.get("Elenco")
    if not saga_key:
        return None

    movie_full = get_movie(movie["id"])
    collection_info = movie_full.get("belongs_to_collection")
    if not collection_info:
        return None

    collection_id = collection_info["id"]
    collection_name = collection_info["name"]
    collection_data = get_collection(collection_id)

    collection_page = find_by_name(COLLECTION_DB_ID, collection_name)
    if not collection_page:
        collection_page = create_collection_page(
            COLLECTION_DB_ID,
            collection_name,
            description=collection_data.get("overview"),
            poster_url=f"https://image.tmdb.org/t/p/original{collection_data.get('poster_path')}"
            if collection_data.get("poster_path") else None
        )
        if collection_page:
            created_collections.append(collection_name)

    for part in sorted(collection_data["parts"], key=lambda x: x.get("release_date", "")):
        if part["id"] == movie["id"]:
            continue
        if find_by_name(MOVIE_DB_ID, part.get("title")):
            continue

        # Obtener créditos
        credits = get_credits(part["id"])
        cast = credits.get("cast", [])
        crew = credits.get("crew", [])

        actor_relations = []
        director_relations = []

        # Actor principal
        if cast:
            actor = cast[0]
            name = actor.get("name")
            person_id = actor.get("id")
            person_data = get_person(person_id)
            image_url = f"https://image.tmdb.org/t/p/original{person_data.get('profile_path')}" if person_data.get("profile_path") else None

            existing = find_person_by_name(PERSON_DB_ID, name, title_prop=person_prop_map.get("Nombre"))
            if not existing:
                created = create_person_page(PERSON_DB_ID, name, role="Actor", prop_map=person_prop_map, image_url=image_url)
                if created:
                    actor_relations.append({"id": created["id"]})
            else:
                actor_relations.append({"id": existing["id"]})

        # Director
        director = next((p for p in crew if p.get("job") == "Director"), None)
        if director:
            name = director.get("name")
            person_id = director.get("id")
            person_data = get_person(person_id)
            image_url = f"https://image.tmdb.org/t/p/original{person_data.get('profile_path')}" if person_data.get('profile_path') else None

            existing = find_person_by_name(PERSON_DB_ID, name, title_prop=person_prop_map.get("Nombre"))
            if not existing:
                created = create_person_page(PERSON_DB_ID, name, role="Director", prop_map=person_prop_map, image_url=image_url)
                if created:
                    director_relations.append({"id": created["id"]})
            else:
                director_relations.append({"id": existing["id"]})

        # Relación Elenco
        extra_props = {}
        if elenco_key and (actor_relations or director_relations):
            extra_props[elenco_key] = {"relation": actor_relations + director_relations}

        # Crear película con relaciones
        create_movie_page(
            db_id=MOVIE_DB_ID,
            movie_data=part,
            prop_map=prop_map,
            saga_page=collection_page,
            genres_dict=genre_dict,
            extra_properties=extra_props
        )
        created_movies.append(part.get("title"))

    return {"relation": [{"id": collection_page["id"]}]} if collection_page else None

def mostrar_resumen(actualizadas, omitidas, fallidas, creadas, colecciones, personas):
    print(f"\n📊 Resumen final:")
    print(f"  🎬 Películas creadas: {len(creadas)}")
    print(f"  📦 Colecciones creadas: {len(colecciones)}")
    print(f"  👤 Personas creadas: {len(personas)}")
    print(f"  ✅ Actualizadas: {len(actualizadas)}")
    print(f"  ⏩ Omitidas: {len(omitidas)}")
    print(f"  ❌ Fallidas: {len(fallidas)}")

    ver_detalle = input("\n¿Desea ver el detalle de cada grupo? (s/n): ").strip().lower()
    if ver_detalle == "s":
        if creadas:
            print("\n🎬 Películas creadas:")
            for t in creadas:
                print(f"  🎬 {t}")
        if colecciones:
            print("\n📦 Colecciones creadas:")
            for c in colecciones:
                print(f"  📦 {c}")
        if personas:
            print("\n👤 Personas creadas:")
            for p in personas:
                print(f"  👤 {p}")
        if actualizadas:
            print("\n✅ Películas actualizadas:")
            for t in actualizadas:
                print(f"  ✅ {t}")
        if fallidas:
            print("\n❌ Películas no encontradas o sin datos válidos:")
            for t in fallidas:
                print(f"  ❌ {t}")
    else:
        print(f"\n🧘 Detalle omitido{'-'*50}")

    ver_omitidas = input("\n¿Desea ver las que se omitieron? (s/n): ").strip().lower()
    if ver_omitidas == 's':
        if omitidas:
            print("\n⏩ Películas omitidas (ya tenían poster):")
            for t in omitidas:
                print(f"  ⏩ {t}")

def main():
    print("\n🚀 Iniciando NotionFlix...\n")
    updated_titles = []
    skipped_titles = []
    failed_titles = []
    created_movies = []
    created_collections = []
    created_people = []

    prop_map = get_database_schema(MOVIE_DB_ID)
    genre_dict = get_genres()
    person_prop_map = get_person_schema(PERSON_DB_ID)
    pages = get_pages(MOVIE_DB_ID)

    for page in pages:
        title = extract_title(page)
        if not title:
            continue
        if has_poster(page, prop_map):
            skipped_titles.append(title)
            continue

        año_prop = page["properties"].get(prop_map.get("Año"))
        año = año_prop["number"] if año_prop and año_prop["number"] else None

        movie = search_movie(title, year=año, interactive=True)
        if not movie:
            failed_titles.append(title)
            continue

        properties = build_properties(movie, title, prop_map, genre_dict)

        # Relación con colección
        saga_relation = handle_collection(movie, prop_map, genre_dict, created_movies, created_collections,person_prop_map)
        saga_key = prop_map.get("Saga")
        if saga_key and saga_relation:
            properties[saga_key] = saga_relation

        credits = get_credits(movie["id"])
        cast = credits.get("cast", [])
        crew = credits.get("crew", [])

        actor_relations = []
        director_relations = []

        # Actor principal
        if cast:
            actor = cast[0]
            name = actor.get("name")
            person_id = actor.get("id")
            person_data = get_person(person_id)
            image_url = f"https://image.tmdb.org/t/p/original{person_data.get('profile_path')}" if person_data.get("profile_path") else None

            existing = find_person_by_name(PERSON_DB_ID, name, title_prop=person_prop_map.get("Nombre"))
            if not existing:
                created = create_person_page(PERSON_DB_ID, name, role="Actor", prop_map=person_prop_map, image_url=image_url)
                if created:
                    actor_relations.append({"id": created["id"]})
                    created_people.append(name)
            else:
                actor_relations.append({"id": existing["id"]})

        # Director
        director = next((p for p in crew if p.get("job") == "Director"), None)
        if director:
            name = director.get("name")
            person_id = director.get("id")
            person_data = get_person(person_id)
            image_url = f"https://image.tmdb.org/t/p/original{person_data.get('profile_path')}" if person_data.get("profile_path") else None

            existing = find_person_by_name(PERSON_DB_ID, name, title_prop=person_prop_map.get("Nombre"))
            if not existing:
                created = create_person_page(PERSON_DB_ID, name, role="Director", prop_map=person_prop_map, image_url=image_url)
                if created:
                    director_relations.append({"id": created["id"]})
                    created_people.append(name)
            else:
                director_relations.append({"id": existing["id"]})


        elenco_key = prop_map.get("Elenco")
        if elenco_key and (actor_relations or director_relations):
            properties[elenco_key] = {"relation": actor_relations + director_relations}

        if properties:
            update_page(page["id"], properties)
            updated_titles.append(title)
            print(f"✅ Página '{title}' actualizada.\n{'-'*50}")
        else:
            print(f"⚠️ No hay datos válidos para actualizar en '{title}'.\n{'-'*50}")
            failed_titles.append(title)

    mostrar_resumen(updated_titles, skipped_titles, failed_titles,
                    created_movies, created_collections, created_people)

    print("\n🏁 Vuelva pronto ! -- NotionFlix\n")

if __name__ == "__main__":
    main()