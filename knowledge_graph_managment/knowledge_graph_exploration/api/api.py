import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
from SPARQLWrapper import SPARQLWrapper, JSON

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Knowledge Graph Exploration API")
ENDPOINT = "https://labs.tib.eu/sdm/ldm_kg/sparql"

monovalue_set = {
    'http://purl.org/dc/terms/modified',
    'http://www.w3.org/2002/07/owl#versionInfo',
    'http://purl.org/dc/terms/license',
    'http://purl.org/dc/terms/description',
    'http://xmlns.com/foaf/0.1/page',
    'http://purl.org/dc/terms/identifier',
    'http://purl.org/dc/terms/issued',
    'http://purl.org/dc/terms/publisher',
    'http://purl.org/dc/terms/title',
    'http://purl.org/spar/datacite/usesIdentifierScheme',
    'http://www.w3.org/2006/vcard/ns#fn',
    'http://www.w3.org/2006/vcard/ns#hasEmail',
    'http://purl.org/dc/terms/accessRights',
    'http://purl.org/dc/terms/language',
    'http://purl.org/dc/terms/conformsTo',
}

prefixes = f"""
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
creator_string = 'http://purl.org/dc/terms/creator'
distribution_string = 'http://www.w3.org/ns/dcat#distribution'
keyword_string = 'http://www.w3.org/ns/dcat#keyword'
landing_page_string = 'http://www.w3.org/ns/dcat#landingPage'
is_described_by_string = 'http://purl.org/spar/datacite/isDescribedBy'
citation_string = 'http://schema.org/citation'

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
            entity_uri = row[entity_name]['value']
            p_value = row['p']['value']

            inner_data = {
                "type": row['o']['type'],
                "value": row['o']['value']
            }
            if 'datatype' in row['o']:
                inner_data['datatype'] = row['o']['datatype']

            grouped_entities[entity_uri].setdefault(p_value, []).append(inner_data)

        # Convert dictionary to flat list for Rust parser
        json_list = []
        for uri, properties in grouped_entities.items():
            json_list.append({"uri": uri, "properties": properties})

        return json_list
    except Exception as e:
        logger.error(f"Error in {entity_name} subquery", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{entity_name} query error: {str(e)}")

def get_bulk_dataset_information_helper(dataset_uris: List[str]) -> dict:
    """
    THE MASTER FUNCTION: Takes ANY number of dataset URIs, queries the entire
    graph in exactly 4 optimized batches, and returns a grouped dictionary.
    """
    if not dataset_uris:
        return {}

    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)

    values_string = " ".join([f"<{uri}>" for uri in dataset_uris])

    # 1. Main Query: Grab top-level properties for ALL datasets at once
    query = f"""
    {prefixes}
    SELECT DISTINCT ?dataset ?p ?o
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

    # Prepare data structures
    final_results = {uri: {} for uri in dataset_uris}

    local_sets = {
        uri: {"type_set": set(), "landing_page_set": set(), "is_described_by_set": set(),
              "citation_set": set(), "creator_set": set(), "distribution_set": set(), "keyword_set": set()}
        for uri in dataset_uris
    }

    global_creator_set = set()
    global_distribution_set = set()
    global_keyword_set = set()

    # Sort the massive response into our local dataset groupings
    for row in main_query_result:
        ds_uri = row['dataset']['value']
        p_value = row['p']['value']

        if ds_uri not in final_results:
            continue

        if p_value in monovalue_set:
            inner_data = {"type": row['o']['type'], "value": row['o']['value']}
            if row['o']['type'] == 'typed-literal' and 'datatype' in row['o']:
                inner_data['datatype'] = row['o']['datatype']
            final_results[ds_uri][p_value] = inner_data
        else:
            o_value = row['o']['value']
            if p_value == type_string:
                local_sets[ds_uri]["type_set"].add(o_value)
            elif p_value == landing_page_string:
                local_sets[ds_uri]["landing_page_set"].add(o_value)
            elif p_value == is_described_by_string:
                local_sets[ds_uri]["is_described_by_set"].add(o_value)
            elif p_value == citation_string:
                local_sets[ds_uri]["citation_set"].add(o_value)
            elif p_value == creator_string:
                local_sets[ds_uri]["creator_set"].add(o_value)
                global_creator_set.add(o_value)
            elif p_value == distribution_string:
                local_sets[ds_uri]["distribution_set"].add(o_value)
                global_distribution_set.add(o_value)
            elif p_value == keyword_string:
                local_sets[ds_uri]["keyword_set"].add(o_value)
                global_keyword_set.add(o_value)

    # 2. Subqueries: Fetch nested properties for ALL datasets using global sets
    creators_data = {item['uri']: item for item in fetch_nested_entities(sparql, global_creator_set, "creator")} if global_creator_set else {}
    distributions_data = {item['uri']: item for item in fetch_nested_entities(sparql, global_distribution_set, "distribution")} if global_distribution_set else {}
    keywords_data = {item['uri']: item for item in fetch_nested_entities(sparql, global_keyword_set, "keyword")} if global_keyword_set else {}

    # 3. Reassemble: Link the deep objects back to their parent datasets
    for ds_uri, sets in local_sets.items():
        if sets["type_set"]:
            final_results[ds_uri][type_string] = list(sets["type_set"])
        if sets["landing_page_set"]:
            final_results[ds_uri][landing_page_string] = list(sets["landing_page_set"])
        if sets["is_described_by_set"]:
            final_results[ds_uri][is_described_by_string] = list(sets["is_described_by_set"])
        if sets["citation_set"]:
            final_results[ds_uri][citation_string] = list(sets["citation_set"])

        if sets["creator_set"]:
            final_results[ds_uri][creator_string] = [creators_data[c] for c in sets["creator_set"] if c in creators_data]
        if sets["distribution_set"]:
            final_results[ds_uri][distribution_string] = [distributions_data[d] for d in sets["distribution_set"] if d in distributions_data]
        if sets["keyword_set"]:
            final_results[ds_uri][keyword_string] = [keywords_data[k] for k in sets["keyword_set"] if k in keywords_data]

    return final_results

# get requests
def get_dataset_information_by_author_orcid_helper(author_orcid: str):
    return get_dataset_information_by_several_author_orcid_helper([author_orcid])

def get_dataset_information_by_author_ldm_id_helper(author_ldm_id: str):
    return get_dataset_information_by_several_author_ldm_id_helper([author_ldm_id])

def get_dataset_information_by_paper_doi_helper(paper_doi: str):
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)
    query = f"""
    {prefixes}

    SELECT DISTINCT
        ?dataset
    WHERE {{
        BIND (<{paper_doi}> as ?is_described_by)
        ?dataset a dcat:Dataset .
        ?dataset datacite:isDescribedBy ?is_described_by .
        ?dataset ?p ?o.
    }}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in several Dataset DOI helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_paper_title_helper(paper_title: str):
    # TODO: Implement SPARQL query here
    return []

def get_dataset_information_by_dataset_doi_helper(dataset_doi: str):
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)
    query = f"""
    {prefixes}

    SELECT DISTINCT
        ?dataset
    WHERE {{
        BIND (<{dataset_doi}> as ?landing_page)
        ?dataset a dcat:Dataset .
        ?dataset dcat:landingPage ?landing_page .
        ?dataset ?p ?o.
    }}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = list(set([row['dataset']['value'] for row in results]))
        return get_bulk_dataset_information_helper(dataset_uris)
    except Exception as e:
        logger.error("SPARQL Query Failed in several Dataset DOI helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_dataset_title_helper(dataset_title: str):
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)

    query = f"""
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct:  <http://purl.org/dc/terms/>
    SELECT DISTINCT ?dataset
    WHERE {{
        ?dataset a dcat:Dataset .
        ?dataset dct:title "{dataset_title}" .
    }}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']
        dataset_uris = [row['dataset']['value'] for row in results]

        # 2. Fetch the deep properties for EACH dataset and group them by URI!
        final_results = {}
        for uri in dataset_uris:
            final_results[uri] = get_dataset_information_by_dataset_ldm_id_helper(uri)

        return final_results

    except Exception as e:
        logger.error("SPARQL Query Failed in Dataset Title helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_dataset_ldm_id_helper(dataset_ldm_id: str):
    bulk_result = get_bulk_dataset_information_helper([dataset_ldm_id])
    return bulk_result.get(dataset_ldm_id, {})

# post requests
def get_dataset_information_by_several_author_orcid_helper(author_orcids: List[str]):
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)
    values_str = " ".join([f"<{orcid}>" for orcid in author_orcids])

    query = f"""
    PREFIX pro: <http://purl.org/spar/pro/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX dct: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?author ?dataset
    WHERE {{
        VALUES ?orcid {{ {values_str} }}

        ?author a pro:Author .
        ?author owl:sameAS ?orcid .

        OPTIONAL {{ ?dataset dct:creator ?author . }}
    }}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']

        author_uris = set()
        dataset_uris = set()

        for row in results:
            if 'author' in row:
                author_uris.add(row['author']['value'])
            if 'dataset' in row:
                dataset_uris.add(row['dataset']['value'])

        final_results = {}

        if dataset_uris:
            final_results.update(get_bulk_dataset_information_helper(list(dataset_uris)))

        if author_uris:
            author_properties_list = fetch_nested_entities(sparql, author_uris, "author")
            for author_data in author_properties_list:
                author_uri = author_data["uri"]

                final_results[author_uri] = author_data["properties"]

        return final_results

    except Exception as e:
        logger.error("SPARQL Query Failed in bulk ORCID helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_author_ldm_id_helper(author_ldm_ids: List[str]):
    sparql = SPARQLWrapper(ENDPOINT)
    sparql.setReturnFormat(JSON)
    values_str = " ".join([f"<{orcid}>" for orcid in author_ldm_ids])

    query = f"""
    PREFIX pro: <http://purl.org/spar/pro/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX dct: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?author ?dataset
    WHERE {{
        VALUES ?author {{ {values_str} }}

        ?author a pro:Author .

        OPTIONAL {{ ?dataset dct:creator ?author . }}
    }}
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()['results']['bindings']

        author_uris = set()
        dataset_uris = set()

        for row in results:
            if 'author' in row:
                author_uris.add(row['author']['value'])
            if 'dataset' in row:
                dataset_uris.add(row['dataset']['value'])

        final_results = {}

        if dataset_uris:
            final_results.update(get_bulk_dataset_information_helper(list(dataset_uris)))

        if author_uris:
            author_properties_list = fetch_nested_entities(sparql, author_uris, "author")
            for author_data in author_properties_list:
                author_uri = author_data["uri"]

                final_results[author_uri] = author_data["properties"]

        return final_results

    except Exception as e:
        logger.error("SPARQL Query Failed in bulk ORCID helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_information_by_several_paper_doi_helper(paper_dois: List[str]):
    # TODO: Implement bulk SPARQL query here
    return []

def get_dataset_information_by_several_paper_title_helper(paper_titles: List[str]):
    # TODO: Implement bulk SPARQL query here
    return []

def get_dataset_information_by_several_dataset_doi_helper(dataset_dois: List[str]):
    # TODO: Implement bulk SPARQL query here
    return []

def get_dataset_information_by_several_dataset_title_helper(dataset_titles: List[str]):
    # TODO: Implement bulk SPARQL query here
    return []

def get_dataset_information_by_several_dataset_ldm_id_helper(dataset_ldm_ids: List[str]):
    # TODO: Implement bulk SPARQL query here
    return []


# author orcid endpoint
@app.get("/get_dataset_information_by_author_orcid")
async def get_dataset_information_by_author_orcid(author_orcid: str = Query(...)):
    try:
        data = get_dataset_information_by_author_orcid_helper(author_orcid)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this ORCID.")
        return {"author_orcid": author_orcid, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Author ORCID: {author_orcid}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_author_orcid")
async def get_dataset_information_by_several_author_orcid(request: AuthorOrcidRequest):
    if not request.author_orcids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_author_orcid_helper(request.author_orcids)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these ORCIDs.")
        return {"requested_count": len(request.author_orcids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Author ORCIDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

# author ldm id endpoint
@app.get("/get_dataset_information_by_author_ldm_id")
async def get_dataset_information_by_author_ldm_id(author_ldm_id: str = Query(...)):
    try:
        data = get_dataset_information_by_author_ldm_id_helper(author_ldm_id)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this LDM ID.")
        return {"author_ldm_id": author_ldm_id, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Author LDM ID: {author_ldm_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_author_ldm_id")
async def get_dataset_information_by_several_author_ldm_id(request: AuthorLdmIdRequest):
    if not request.author_ldm_ids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_author_ldm_id_helper(request.author_ldm_ids)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these LDM IDs.")
        return {"requested_count": len(request.author_ldm_ids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Author LDM IDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

# paper doi endpoint
@app.get("/get_dataset_information_by_paper_doi")
async def get_dataset_information_by_paper_doi(paper_doi: str = Query(...)):
    try:
        data = get_dataset_information_by_paper_doi_helper(paper_doi)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Paper DOI.")
        return {"paper_doi": paper_doi, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Paper DOI: {paper_doi}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_paper_doi")
async def get_multiple_by_paper_doi(request: PaperDoiRequest):
    if not request.paper_dois:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_paper_doi_helper(request.paper_dois)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Paper DOIs.")
        return {"requested_count": len(request.paper_dois), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Paper DOIs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

# paper title endpoint
@app.get("/get_dataset_information_by_paper_title")
async def get_dataset_information_by_paper_title(paper_title: str = Query(...)):
    try:
        data = get_dataset_information_by_paper_title_helper(paper_title)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Paper Title.")
        return {"paper_title": paper_title, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Paper Title: {paper_title}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_paper_title")
async def get_dataset_information_by_several_paper_title(request: PaperTitleRequest):
    if not request.paper_titles:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_paper_title_helper(request.paper_titles)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Paper Titles.")
        return {"requested_count": len(request.paper_titles), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Paper Titles", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

# dataset doi endpoint
@app.get("/get_dataset_information_by_dataset_doi")
async def get_dataset_information_by_dataset_doi(dataset_doi: str = Query(...)):
    try:
        data = get_dataset_information_by_dataset_doi_helper(dataset_doi)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Dataset DOI.")
        return {"dataset_doi": dataset_doi, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Dataset DOI: {dataset_doi}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_dataset_doi")
async def get_dataset_information_by_several_dataset_doi(request: DatasetDoiRequest):
    if not request.dataset_dois:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_dataset_doi_helper(request.dataset_dois)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Dataset DOIs.")
        return {"requested_count": len(request.dataset_dois), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Dataset DOIs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

# dataset title endpoint
@app.get("/get_dataset_information_by_dataset_title")
async def get_dataset_information_by_dataset_title(dataset_title: str = Query(...)):
    try:
        data = get_dataset_information_by_dataset_title_helper(dataset_title)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Dataset Title.")
        return {"dataset_title": dataset_title, "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Dataset Title: {dataset_title}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_dataset_title")
async def get_dataset_information_by_several_dataset_title(request: DatasetTitleRequest):
    if not request.dataset_titles:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_dataset_title_helper(request.dataset_titles)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Dataset Titles.")
        return {"requested_count": len(request.dataset_titles), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Dataset Titles", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

# dataset ldm id endpoint
@app.get("/get_dataset_information_by_dataset_ldm_id")
async def get_dataset_information_by_dataset_ldm_id(dataset_ldm_id: str = Query(...)):
    try:
        data = get_dataset_information_by_dataset_ldm_id_helper(dataset_ldm_id)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for this Dataset LDM ID.")
        return {"dataset_ldm_id": dataset_ldm_id, "results": {dataset_ldm_id: data}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching by Dataset LDM ID: {dataset_ldm_id}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.post("/get_dataset_information_by_several_dataset_ldm_id")
async def get_dataset_information_by_several_dataset_ldm_id(request: DatasetLdmIdRequest):
    if not request.dataset_ldm_ids:
        raise HTTPException(status_code=400, detail="List cannot be empty.")
    try:
        data = get_dataset_information_by_several_dataset_ldm_id_helper(request.dataset_ldm_ids)
        if not data:
            raise HTTPException(status_code=404, detail="No datasets found for these Dataset LDM IDs.")
        return {"requested_count": len(request.dataset_ldm_ids), "found_count": len(data), "results": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching multiple Dataset LDM IDs", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal SPARQL Error")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5742)
