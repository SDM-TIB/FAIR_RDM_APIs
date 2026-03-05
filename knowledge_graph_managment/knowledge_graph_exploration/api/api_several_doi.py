from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
from SPARQLWrapper import SPARQLWrapper, JSON
import uvicorn

app = FastAPI(title="SPARQL DOI Lookup API")

ENDPOINT = "https://labs.tib.eu/sdm/ldm_kg/sparql"

class DOIRequest(BaseModel):
    dois: List[str]

def run_batch_sparql_query(doi_list: List[str]):
    sparql = SPARQLWrapper(ENDPOINT)

    formatted_dois = " ".join([f"<{d}>" for d in doi_list])

    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX datacite: <http://purl.org/spar/datacite/>

    SELECT DISTINCT ?doi ?dataset ?author ?author_label ?title ?contact_person ?license
    WHERE {{
      VALUES ?doi {{ {formatted_dois} }}
      ?dataset    a                         dcat:Dataset .
      ?dataset    datacite:isDescribedBy    ?doi .
      ?dataset    dct:creator               ?author .
      ?dataset    dct:title                 ?title .
      ?dataset    dcat:contactPoint         ?contact_person .
      ?dataset    dct:license               ?license .
      ?author     rdfs:label                ?author_label .
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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}

@app.post("/get_paper_info_by_several_doi")
async def get_paper_info_by_several_doi(request: DOIRequest):
    if not request.dois:
        raise HTTPException(status_code=400, detail="DOI list cannot be empty.")

    data = run_batch_sparql_query(request.dois)

    if not data:
        raise HTTPException(status_code=404, detail="No dataset found with that DOI.")

    return {
        "requested_count": len(request.dois),
        "found_count": len(data),
        "results": data
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
