from fastapi import FastAPI, HTTPException, Query
from SPARQLWrapper import SPARQLWrapper, JSON
import uvicorn

app = FastAPI(title="SPARQL DOI Lookup API")

ENDPOINT = "https://labs.tib.eu/sdm/ldm_kg/sparql"

def get_paper_attributes_by_doi_helper(doi_value: str):
    sparql = SPARQLWrapper(ENDPOINT)

    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX datacite: <http://purl.org/spar/datacite/>

    SELECT DISTINCT ?dataset ?author ?author_label ?title ?contact_person ?license
    WHERE {
      ?dataset    a                         dcat:Dataset .
      ?dataset    datacite:isDescribedBy    ?doi .
      ?dataset    dct:creator               ?author .
      ?dataset    dct:title                 ?title .
      ?dataset    dcat:contactPoint         ?contact_person .
      ?dataset    dct:license               ?license .
      ?author     rdfs:label                ?author_label .

      FILTER(CONTAINS(STR(?doi), "%s"))
    }
    """ % doi_value

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

@app.get("/get_paper_attributes_by_doi")
async def get_paper_attributes_by_doi(doi: str = Query(..., description="return papers belonging to a doi")):
    data = get_paper_attributes_by_doi_helper(doi)

    if not data:
        raise HTTPException(status_code=404, detail="No dataset found with that DOI.")

    return {"doi": doi, "results": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
