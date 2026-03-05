from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
from SPARQLWrapper import SPARQLWrapper, JSON
import uvicorn

app = FastAPI(title="Knowledge Graph Exploration API")

ENDPOINT = "https://labs.tib.eu/sdm/ldm_kg/sparql"

class DOIRequest(BaseModel):
    dois: List[str]

class ORCIDRequest(BaseModel):
    orcid: str

def get_dataset_attributes_by_paper_doi_helper(input_paper_doi: str):
    sparql = SPARQLWrapper(ENDPOINT)

    query = f"""
    PREFIX rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcat:     <http://www.w3.org/ns/dcat#>
    PREFIX dct:      <http://purl.org/dc/terms/>
    PREFIX datacite: <http://purl.org/spar/datacite/>
    PREFIX vcard:    <http://www.w3.org/2006/vcard/ns#>

    SELECT DISTINCT
      ?dataset ?doi ?author ?author_label ?title ?contact_person ?license
    WHERE {{
      bind (<{input_paper_doi}> as ?doi)
      ?dataset    a                         dcat:Dataset .
      ?dataset    datacite:isDescribedBy    ?doi .
      optional {{
        ?dataset dct:creator ?author .
        ?author rdfs:label ?author_label
      }} .
      optional {{ ?dataset dct:title ?title }} .
      optional {{ ?dataset vcard:fn ?contact_person }} .
      optional {{ ?dataset dct:license ?license }} .
    }}
    """

    print(query)

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]

        return [{k: v['value'] for k, v in row.items()} for row in bindings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_attributes_by_several_paper_doi_helper(input_paper_doi_list: List[str]):
    sparql = SPARQLWrapper(ENDPOINT)

    formatted_dois = " ".join([f"<{d}>" for d in input_paper_doi_list])

    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX datacite: <http://purl.org/spar/datacite/>
    PREFIX vcard:    <http://www.w3.org/2006/vcard/ns#>

    SELECT DISTINCT
      ?dataset ?doi ?author ?author_label ?title ?contact_person ?license
    WHERE {{
      VALUES ?doi {{ {formatted_dois} }}
      ?dataset    a                         dcat:Dataset .
      ?dataset    datacite:isDescribedBy    ?doi .
     optional {{
        ?dataset dct:creator ?author .
        ?author rdfs:label ?author_label
      }} .
      optional {{ ?dataset dct:title ?title }} .
      optional {{ ?dataset ?contact_person }} .
      optional {{ ?dataset dct:license ?license }} .
    }}
    """

    # print(query)

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]

        return [{k: v['value'] for k, v in row.items()} for row in bindings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

def get_dataset_attributes_by_author_orcid_helper(orcid: str):
    sparql = SPARQLWrapper(ENDPOINT)

    # get the ldm id of a author from the orcid
    author_query = f"""
    PREFIX pro: <http://purl.org/spar/pro/>

    SELECT DISTINCT ?author
    WHERE {{
        ?author rdf:type pro:Author .
        ?author owl:sameAS <{orcid}> .
    }}
    """

    #print(query)

    sparql.setQuery(author_query)
    sparql.setReturnFormat(JSON)

    try:
        author_id = sparql.query().convert()["results"]["bindings"][0]["author"]["value"]

        dataset_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dct: <http://purl.org/dc/terms/>
        PREFIX datacite: <http://purl.org/spar/datacite/>
        PREFIX pro: <http://purl.org/spar/pro/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT DISTINCT
          ?dataset ?author ?author_label ?orcid ?title ?contact_person ?license
        WHERE {{
          BIND (<{author_id}> as ?author)
          ?author     rdf:type             pro:Author .
          ?author     owl:sameAS           ?orcid .
          ?author     rdfs:label           ?author_label .
          ?dataset    rdf:type             dcat:Dataset .
          ?dataset    dct:creator          ?author .
          ?dataset    dct:title            ?title .
          optional {{ ?dataset vcard:fn ?contact_person }} .
          optional {{ ?dataset dct:license ?license }} .
        }}
        """

        # print(dataset_query)

        sparql.setQuery(dataset_query)
        sparql.setReturnFormat(JSON)

        try:
            bindings = sparql.query().convert()["results"]["bindings"]

            return [{k: v['value'] for k, v in row.items()} for row in bindings]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")
    return {}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}

@app.get("/get_dataset_attributes_by_paper_doi")
async def get_dataset_attributes_by_paper_doi(doi: str = Query(..., description="return papers belonging to a doi")):
    data = get_dataset_attributes_by_paper_doi_helper(doi)

    if not data:
        raise HTTPException(status_code=404, detail="no paper found with that DOI.")

    return {"doi": doi, "results": data}

@app.post("/get_dataset_attributes_by_paper_doi")
async def get_dataset_attributes_by_paper_doi(request: DOIRequest):
    if not request.dois:
        raise HTTPException(status_code=400, detail="DOI list cannot be empty.")

    data = get_dataset_attributes_by_several_paper_doi_helper(request.dois)

    if not data:
        raise HTTPException(status_code=404, detail="no paper found with that DOI.")

    return {
        "requested_count": len(request.dois),
        "found_count": len(data),
        "results": data
    }

@app.get("/get_dataset_attributes_by_author_orcid")
async def get_dataset_attributes_by_author_orcid(orcid: str = Query(..., description="return papers belonging to a doi")):
    data = get_dataset_attributes_by_author_orcid_helper(orcid)

    if not data:
        raise HTTPException(status_code=404, detail="no dataset found in correlation to that author.")

    return {"orcid": orcid, "results": data}

@app.post("/get_dataset_attributes_by_author_orcid")
async def get_dataset_attributes_by_author_orcid(request: ORCIDRequest):
    if not request.orcid:
        raise HTTPException(status_code=400, detail="ORCID can not be empty.")

    data = get_dataset_attributes_by_author_orcid_helper(request.orcid)

    if not data:
        raise HTTPException(status_code=404, detail="no dataset found in correlation to that author.")

    return {"orcid": request.orcid, "results": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
