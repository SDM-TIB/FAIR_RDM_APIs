import logging
import uvicorn
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Tuple
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from rdflib import Literal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Knowledge Graph Exploration API")
ENDPOINT = os.environ['CKANEXT__KG_EXPLORATION__ENDPOINT']

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_sparql_client():
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)
    sparql.setMethod(POST)
    return sparql

monovalue_set = {
    'http://purl.org/dc/terms/modified',
    'http://www.w3.org/2002/07/owl#versionInfo',
    'http://purl.org/dc/terms/license',
    'http://purl.org/dc/terms/description',
    'http://xmlns.com/foaf/0.1/page',
    'http://purl.org/dc/terms/identifier',
    'http://purl.org/dc/terms/issued',
    'http://purl.org/dc/terms/title',
    'http://purl.org/spar/datacite/usesIdentifierScheme',
    'http://www.w3.org/2006/vcard/ns#fn',
    'http://www.w3.org/2006/vcard/ns#hasEmail',
    'http://purl.org/dc/terms/accessRights',
    'http://purl.org/dc/terms/language',
    'http://purl.org/dc/terms/conformsTo',
}

prefixes = """
PREFIX rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcat:     <http://www.w3.org/ns/dcat#>
PREFIX dct:      <http://purl.org/dc/terms/>
PREFIX datacite: <http://purl.org/spar/datacite/>
PREFIX pro:      <http://purl.org/spar/pro/>
PREFIX owl:      <http://www.w3.org/2002/07/owl#>
PREFIX schema:   <http://schema.org/>
PREFIX orgk:     <http://orkg.org/orkg/class/>
"""

type_string = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
label_string = 'http://www.w3.org/2000/01/rdf-schema#label'
same_as_string = 'http://www.w3.org/2002/07/owl#sameAS'
creator_string = 'http://purl.org/dc/terms/creator'
distribution_string = 'http://www.w3.org/ns/dcat#distribution'
keyword_string = 'http://www.w3.org/ns/dcat#keyword'
landing_page_string = 'http://www.w3.org/ns/dcat#landingPage'
is_described_by_string = 'http://purl.org/spar/datacite/isDescribedBy'
citation_string = 'http://schema.org/citation'
publisher_string = 'http://purl.org/dc/terms/publisher'

# --- MODELS ---
class AuthorNameRequest(BaseModel):
    author_names: List[str]

class AuthorOrcidRequest(BaseModel):
    author_orcids: List[str]

class AuthorLdmIdRequest(BaseModel):
    author_ldm_ids: List[str]

class PaperDoiRequest(BaseModel):
    paper_dois: List[str]

class PaperTitleRequest(BaseModel):
    paper_titles: List[str]

class DatasetDoiRequest(BaseModel):
    dataset_dois: List[str]

class DatasetTitleRequest(BaseModel):
    dataset_titles: List[str]

class DatasetLdmIdRequest(BaseModel):
    dataset_ldm_ids: List[str]

class KeywordRequest(BaseModel):
    keywords: List[str]

class PublisherIdRequest(BaseModel):
    publisher_ids: List[str]

# --- BULK HYDRATION ENGINE ---
def _parse_o_node(o_node: dict) -> dict:
    inner_data = {"type": o_node['type'], "value": o_node['value']}
    if 'datatype' in o_node:
        inner_data['datatype'] = o_node['datatype']
    return inner_data

def _process_nested_row(row: dict, entity_name: str, grouped: dict):
    entity_uri = row[entity_name]['value']
    p_value = row['p']['value']
    inner_data = _parse_o_node(row['o'])
    grouped[entity_uri].setdefault(p_value, []).append(inner_data)

def _map_bulk_property(ds_uri: str, p_val: str, o_val: str, local_sets: dict, global_sets: dict):
    mapping = {
        type_string: ("type_set", None),
        landing_page_string: ("landing_page_set", None),
        is_described_by_string: ("is_described_by_set", None),
        citation_string: ("citation_set", None),
        creator_string: ("creator_set", "creator"),
        distribution_string: ("distribution_set", "distribution"),
        publisher_string: ("publisher_set", "publisher"),
        keyword_string: ("keyword_set", "keyword"),
    }
    if p_val not in mapping:
        return

    local_key, global_key = mapping[p_val]
    local_sets[ds_uri][local_key].add(o_val)
    if global_key:
        global_sets[global_key].add(o_val)

def _process_bulk_row(row: dict, final_results: dict, local_sets: dict, global_sets: dict):
    ds_uri = row['dataset']['value']
    p_val = row['p']['value']

    if ds_uri not in final_results:
        return

    if p_val in monovalue_set:
        final_results[ds_uri][p_val] = _parse_o_node(row['o'])
        return

    o_val = row['o']['value']
    _map_bulk_property(ds_uri, p_val, o_val, local_sets, global_sets)

def _reassemble_dataset(ds_uri: str, sets: dict, final_results: dict, nested_data: dict):
    if sets["type_set"]:
        final_results[ds_uri][type_string] = list(sets["type_set"])
    if sets["landing_page_set"]:
        final_results[ds_uri][landing_page_string] = list(sets["landing_page_set"])
    if sets["is_described_by_set"]:
        final_results[ds_uri][is_described_by_string] = list(sets["is_described_by_set"])
    if sets["citation_set"]:
        final_results[ds_uri][citation_string] = list(sets["citation_set"])

    creators = nested_data.get("creator", {})
    dists = nested_data.get("distribution", {})
    keys = nested_data.get("keyword", {})
    pubs = nested_data.get("publisher", {})

    if sets["creator_set"]:
        final_results[ds_uri][creator_string] = [creators[c] for c in sets["creator_set"] if c in creators]
    if sets["distribution_set"]:
        final_results[ds_uri][distribution_string] = [dists[d] for d in sets["distribution_set"] if d in dists]
    if sets["keyword_set"]:
        final_results[ds_uri][keyword_string] = [keys[k] for k in sets["keyword_set"] if k in keys]
    if sets["publisher_set"]:
        final_results[ds_uri][publisher_string] = [pubs[p] for p in sets["publisher_set"] if p in pubs]

def fetch_nested_entities(sparql: SPARQLWrapper, uri_set: set, entity_name: str) -> List[dict]:
    if not uri_set:
        return []

    values_string = " ".join([f"<{uri}>" for uri in uri_set])
    query = f"""
    SELECT ?{entity_name} ?p ?o
    WHERE {{
      VALUES ?{entity_name} {{ {values_string} }}
      ?{entity_name} ?p ?o .
    }}
    """
    sparql.setQuery(query)

    try:
        query_result = sparql.query().convert()['results']['bindings']
        grouped_entities = {uri: {} for uri in uri_set}

        for row in query_result:
            _process_nested_row(row, entity_name, grouped_entities)

        json_list = []
        for uri, properties in grouped_entities.items():
            json_list.append({"uri": uri, "properties": properties})

        return json_list
    except Exception as e:
        logger.error(f"Error in {entity_name} subquery", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{entity_name} query error: {str(e)}")

def get_bulk_dataset_information_helper(dataset_uris: List[str]) -> dict:
    if not dataset_uris:
        return {}

    sparql = get_sparql_client()
    values_string = " ".join([f"<{uri}>" for uri in dataset_uris])

    query = f"""
    {prefixes}
    SELECT DISTINCT
        ?dataset ?p ?o
    WHERE {{
        VALUES ?dataset {{ {values_string} }}
        ?dataset ?p ?o .
    }}
    """

    sparql.setQuery(query)
    try:
        main_query_result = sparql.query().convert()['results']['bindings']
    except Exception as e:
        logger.error("Error in bulk main query", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk main query error: {str(e)}")

    final_results = {uri: {} for uri in dataset_uris}
    local_sets = {
        uri: {"type_set": set(), "landing_page_set": set(), "is_described_by_set": set(),
              "citation_set": set(), "creator_set": set(), "distribution_set": set(), "keyword_set": set(),
              "publisher_set": set()}
        for uri in dataset_uris
    }

    global_sets = {"creator": set(), "distribution": set(), "keyword": set(), "publisher": set()}

    for row in main_query_result:
        _process_bulk_row(row, final_results, local_sets, global_sets)

    nested_data = {}
    for entity in ["creator", "distribution", "keyword", "publisher"]:
        if global_sets[entity]:
            fetched = fetch_nested_entities(sparql, global_sets[entity], entity)
            nested_data[entity] = {item['uri']: item for item in fetched}

    for ds_uri, sets in local_sets.items():
        _reassemble_dataset(ds_uri, sets, final_results, nested_data)

    return final_results


# --- RESOLUTION HELPERS ---
def translate_orcids_to_ldm_ids(author_orcids: List[str]) -> List[str]:
    if not author_orcids: return []
    sparql = get_sparql_client()
    values_str = " ".join([f"<{orcid}>" for orcid in author_orcids])
    query = f"""
    PREFIX pro: <http://purl.org/spar/pro/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT DISTINCT ?author
    WHERE {{
        VALUES ?orcid {{ {values_str} }}
        ?author a pro:Author .
        ?author owl:sameAS ?orcid .
    }}
    """
    sparql.setQuery(query)
    try:
        results = sparql.query().convert()['results']['bindings']
        return list(set(row['author']['value'] for row in results if 'author' in row))
    except Exception as e:
        logger.error("Error translating ORCIDs to LDM IDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Translation SPARQL Error")

def translate_names_to_ldm_ids(author_names: List[str]) -> List[str]:
    if not author_names: return []
    sparql = get_sparql_client()
    values_str = " ".join([Literal(name).n3() for name in author_names])
    query = f"""
    PREFIX pro: <http://purl.org/spar/pro/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?author
    WHERE {{
        VALUES ?name {{ {values_str} }}
        ?author a pro:Author .
        ?author rdfs:label ?name .
    }}
    """
    sparql.setQuery(query)
    try:
        results = sparql.query().convert()['results']['bindings']
        return list(set(row['author']['value'] for row in results if 'author' in row))
    except Exception as e:
        logger.error("Error translating Names to LDM IDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Translation SPARQL Error")

def _inject_same_as(props: dict, orcid_data_map: dict):
    if same_as_string not in props:
        return props

    nested_same_as_list = []
    for raw_s_node in props[same_as_string]:
        s_uri = raw_s_node["value"]
        real_orcid_props = orcid_data_map.get(s_uri, {})

        if type_string not in real_orcid_props:
            real_orcid_props[type_string] = [{"type": "uri", "value": "http://purl.org/spar/pro/Author"}]

        nested_same_as_list.append({"uri": s_uri, "properties": real_orcid_props})

    props[same_as_string] = nested_same_as_list
    return props


# --- PAGINATED FETCH HELPERS ---

def get_dataset_information_by_several_author_ldm_id_paginated_helper(author_ldm_ids: List[str], limit: int = 49, offset: int = 0):
    if not author_ldm_ids:
        return {}

    sparql = get_sparql_client()
    values_str = " ".join([f"<{uri}>" for uri in author_ldm_ids])

    # 1. Fetch paginated datasets
    query_ds = f"""
    {prefixes}
    SELECT DISTINCT ?dataset WHERE {{
        VALUES ?author {{ {values_str} }}
        ?dataset a dcat:Dataset .
        ?dataset dct:creator ?author .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query_ds)
        ds_results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([r['dataset']['value'] for r in ds_results]))

        final_results = {}
        if dataset_uris:
            final_results.update(get_bulk_dataset_information_helper(dataset_uris))

        # 2. Fetch Author Node Properties (even if 0 datasets returned)
        query_author = f"""
        {prefixes}
        SELECT DISTINCT ?author ?same_as WHERE {{
            VALUES ?author {{ {values_str} }}
            ?author a pro:Author .
            OPTIONAL {{ ?author owl:sameAS ?same_as . }}
        }}
        """
        sparql.setQuery(query_author)
        author_results = sparql.query().convert()['results']['bindings']

        author_uris = set()
        same_as_uris = set()
        for row in author_results:
            author_uris.add(row['author']['value'])
            if 'same_as' in row:
                same_as_uris.add(row['same_as']['value'])

        orcid_data_map = {}
        if same_as_uris:
            same_as_props = fetch_nested_entities(sparql, same_as_uris, "same_as_entity")
            for item_data in same_as_props:
                item_uri = item_data["uri"]
                item_props = item_data["properties"]
                orcid_data_map[item_uri] = item_props
                final_results[item_uri] = item_props

        if author_uris:
            author_props = fetch_nested_entities(sparql, author_uris, "author")
            for author_data in author_props:
                author_uri = author_data["uri"]
                props = _inject_same_as(author_data["properties"], orcid_data_map)
                final_results[author_uri] = props

        return final_results
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Author helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_publisher_paginated_helper(publisher_ids: List[str], limit: int = 49, offset: int = 0):
    if not publisher_ids:
        return {}

    sparql = get_sparql_client()
    formatted_publishers = [f"<{pid}>" for pid in publisher_ids]
    values_str = " ".join(formatted_publishers)

    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset
    WHERE {{
        VALUES ?publisher {{ {values_str} }}
        ?dataset a dcat:Dataset .
        ?dataset dct:publisher ?publisher .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))

        if not dataset_uris:
            return {}
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Publisher helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_keyword_paginated_helper(keywords: List[str], limit: int = 49, offset: int = 0):
    if not keywords:
        return {}

    sparql = get_sparql_client()
    formatted_keywords = []
    for kw in keywords:
        if kw.startswith("http://") or kw.startswith("https://"):
            formatted_keywords.append(f"<{kw}>")
        else:
            formatted_keywords.append(Literal(kw).n3())
    values_str = " ".join(formatted_keywords)

    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset
    WHERE {{
        VALUES ?value {{ {values_str} }}
        ?dataset a dcat:Dataset .
        ?dataset dcat:keyword ?keyword .
        ?keyword rdfs:label ?value .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))

        if not dataset_uris:
            return {}
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Keyword helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_paper_doi_paginated_helper(paper_dois: List[str], limit: int = 49, offset: int = 0):
    if not paper_dois: return {}
    sparql = get_sparql_client()
    clean_dois = [d if d.startswith("http") else f"https://doi.org/{d}" for d in paper_dois]
    values_str = " ".join([f"<{doi}>" for doi in clean_dois])

    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset
    WHERE {{
        VALUES ?is_described_by {{ {values_str} }}
        ?dataset a dcat:Dataset .
        ?dataset datacite:isDescribedBy ?is_described_by .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))
        if not dataset_uris: return {}
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Paper DOI helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_paper_title_paginated_helper(paper_titles: List[str], limit: int = 49, offset: int = 0):
    if not paper_titles: return {}
    sparql = get_sparql_client()
    values_str = " ".join([Literal(title).n3() for title in paper_titles])

    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset
    WHERE {{
        VALUES ?title {{ {values_str} }}
        ?paper a orgk:Paper .
        ?paper rdfs:label ?title .
        ?dataset a dcat:Dataset .
        ?dataset datacite:isDescribedBy ?paper .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))
        if not dataset_uris: return {}
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Paper Title helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_dataset_doi_paginated_helper(dataset_dois: List[str], limit: int = 49, offset: int = 0):
    if not dataset_dois: return {}
    sparql = get_sparql_client()
    clean_dois = [d if d.startswith("http") else f"https://doi.org/{d}" for d in dataset_dois]
    values_str = " ".join([f"<{doi}>" for doi in clean_dois])

    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset
    WHERE {{
        VALUES ?source {{ {values_str} }}
        ?dataset a dcat:Dataset .
        ?dataset dct:source ?source .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))
        if not dataset_uris: return {}
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Dataset DOI helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_dataset_title_paginated_helper(dataset_titles: List[str], limit: int = 49, offset: int = 0):
    if not dataset_titles: return {}
    sparql = get_sparql_client()
    values_str = " ".join([Literal(title).n3() for title in dataset_titles])

    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset
    WHERE {{
        VALUES ?title {{ {values_str} }}
        ?dataset a dcat:Dataset .
        ?dataset dct:title ?title .
    }}
    ORDER BY ?dataset
    LIMIT {limit}
    OFFSET {offset}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))
        if not dataset_uris: return {}
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in Paginated Dataset Title helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_dataset_ldm_id_paginated_helper(dataset_ldm_ids: List[str], limit: int = 49, offset: int = 0):
    if not dataset_ldm_ids: return {}
    sliced_ids = dataset_ldm_ids[offset:offset+limit]
    if not sliced_ids: return {}
    return get_bulk_dataset_information_helper(sliced_ids)


# --- AUTHOR ENDPOINTS ---

@app.get("/get_dataset_information_by_author_orcid")
async def get_dataset_information_by_author_orcid(
    author_orcid: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        ldm_ids = translate_orcids_to_ldm_ids([author_orcid])
        data = get_dataset_information_by_several_author_ldm_id_paginated_helper(ldm_ids, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this ORCID.")
        return {"author_orcid": author_orcid, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Author ORCID: {author_orcid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_author_orcid")
async def get_dataset_information_by_several_author_orcid(
    request: AuthorOrcidRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.author_orcids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        ldm_ids = translate_orcids_to_ldm_ids(request.author_orcids)
        data = get_dataset_information_by_several_author_ldm_id_paginated_helper(ldm_ids, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these ORCIDs.")
        return {"requested_count": len(request.author_orcids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Author ORCIDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


@app.get("/get_dataset_information_by_author_name")
async def get_dataset_information_by_author_name(
    author_name: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        name_list = [name.strip() for name in author_name.split(",") if name.strip()]
        ldm_ids = translate_names_to_ldm_ids(name_list)
        data = get_dataset_information_by_several_author_ldm_id_paginated_helper(ldm_ids, limit, offset)

        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these names.")
        return {"author_name": author_name, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Author name(s): {author_name}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_author_name")
async def get_dataset_information_by_several_author_name(
    request: AuthorNameRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.author_names:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        ldm_ids = translate_names_to_ldm_ids(request.author_names)
        data = get_dataset_information_by_several_author_ldm_id_paginated_helper(ldm_ids, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Names.")
        return {"requested_count": len(request.author_names), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Author Names", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


@app.get("/get_dataset_information_by_author_ldm_id")
async def get_dataset_information_by_author_ldm_id(
    author_ldm_id: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_author_ldm_id_paginated_helper([author_ldm_id], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this LDM ID.")
        return {"author_ldm_id": author_ldm_id, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Author LDM ID: {author_ldm_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_author_ldm_id")
async def get_dataset_information_by_several_author_ldm_id(
    request: AuthorLdmIdRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.author_ldm_ids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_author_ldm_id_paginated_helper(request.author_ldm_ids, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these LDM IDs.")
        return {"requested_count": len(request.author_ldm_ids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Author LDM IDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


# --- PAPER ENDPOINTS ---

@app.get("/get_dataset_information_by_paper_doi")
async def get_dataset_information_by_paper_doi(
    paper_doi: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_paper_doi_paginated_helper([paper_doi], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Paper DOI.")
        return {"paper_doi": paper_doi, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Paper DOI: {paper_doi}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_paper_doi")
async def get_dataset_information_by_several_by_paper_doi(
    request: PaperDoiRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.paper_dois:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_paper_doi_paginated_helper(request.paper_dois, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Paper DOIs.")
        return {"requested_count": len(request.paper_dois), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Paper DOIs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.get("/get_dataset_information_by_paper_title")
async def get_dataset_information_by_paper_title(
    paper_title: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_paper_title_paginated_helper([paper_title], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Paper Title.")
        return {"paper_title": paper_title, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Paper Title: {paper_title}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_paper_title")
async def get_dataset_information_by_several_paper_title(
    request: PaperTitleRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.paper_titles:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_paper_title_paginated_helper(request.paper_titles, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Paper Titles.")
        return {"requested_count": len(request.paper_titles), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Paper Titles", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


# --- DATASET ENDPOINTS ---

@app.get("/get_dataset_information_by_dataset_doi")
async def get_dataset_information_by_dataset_doi(
    dataset_doi: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_dataset_doi_paginated_helper([dataset_doi], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Dataset DOI.")
        return {"dataset_doi": dataset_doi, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Dataset DOI: {dataset_doi}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_dataset_doi")
async def get_dataset_information_by_several_dataset_doi(
    request: DatasetDoiRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.dataset_dois:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_dataset_doi_paginated_helper(request.dataset_dois, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Dataset DOIs.")
        return {"requested_count": len(request.dataset_dois), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Dataset DOIs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


@app.get("/get_dataset_information_by_dataset_title")
async def get_dataset_information_by_dataset_title(
    dataset_title: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_dataset_title_paginated_helper([dataset_title], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Dataset Title.")
        return {"dataset_title": dataset_title, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Dataset Title: {dataset_title}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_dataset_title")
async def get_dataset_information_by_several_dataset_title(
    request: DatasetTitleRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.dataset_titles:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_dataset_title_paginated_helper(request.dataset_titles, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Dataset Titles.")
        return {"requested_count": len(request.dataset_titles), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Dataset Titles", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


@app.get("/get_dataset_information_by_dataset_ldm_id")
async def get_dataset_information_by_dataset_ldm_id(
    dataset_ldm_id: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_dataset_ldm_id_paginated_helper([dataset_ldm_id], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Dataset LDM ID.")
        return {"dataset_ldm_id": dataset_ldm_id, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Dataset LDM ID: {dataset_ldm_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_dataset_ldm_id")
async def get_dataset_information_by_several_dataset_ldm_id(
    request: DatasetLdmIdRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.dataset_ldm_ids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_dataset_ldm_id_paginated_helper(request.dataset_ldm_ids, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Dataset LDM IDs.")
        return {"requested_count": len(request.dataset_ldm_ids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Dataset LDM IDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


# --- KEYWORD ENDPOINTS ---

@app.get("/get_dataset_information_by_keyword")
async def get_dataset_information_by_keyword(
    keyword: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        keyword_list = [kw.strip() for kw in keyword.split(",") if kw.strip()]
        data = get_dataset_information_by_several_keyword_paginated_helper(keyword_list, limit, offset)

        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this keyword.")
        return {"keyword": keyword, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Keyword: {keyword}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_keyword")
async def get_dataset_information_by_several_keyword(
    request: KeywordRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.keywords:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_keyword_paginated_helper(request.keywords, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Keywords.")
        return {"requested_count": len(request.keywords), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Keywords", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


# --- PUBLISHER ENDPOINTS ---

@app.get("/get_dataset_information_by_publisher")
async def get_dataset_information_by_publisher(
    publisher_id: str = Query(...),
    limit: int = Query(49, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    try:
        data = get_dataset_information_by_several_publisher_paginated_helper([publisher_id], limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Publisher ID.")
        return {"publisher_id": publisher_id, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Publisher ID: {publisher_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_publisher")
async def get_dataset_information_by_several_publisher(
    request: PublisherIdRequest,
    limit: int = Query(1000, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    if not request.publisher_ids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_publisher_paginated_helper(request.publisher_ids, limit, offset)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Publishers.")
        return {"requested_count": len(request.publisher_ids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Publishers", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5742)
