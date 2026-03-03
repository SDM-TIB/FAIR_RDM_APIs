from fastapi import FastAPI, HTTPException, Query
from SPARQLWrapper import SPARQLWrapper, JSON
import uvicorn

app = FastAPI(title="SPARQL DOI Lookup API")

ENDPOINT = "https://labs.tib.eu/sdm/ldm_kg/sparql"

# i dont know why but i need to split this query into seperate parts because
# the query would time out
def run_sparql_query(orcid: str):
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
          ?author     rdf:type       pro:Author .
          ?author     owl:sameAS     ?orcid .
          ?author     rdfs:label     ?author_label .
          ?dataset    a              dcat:Dataset .
          ?dataset    dct:creator    ?author .
          ?dataset    dct:title      ?title .
          ?dataset    dcat:contactPoint    ?contact_person .
           optional {{ ?dataset dct:license ?license }}
          FILTER (CONTAINS(STR(?author), "{author_id}"))
        }}
        """

        # print(dataset_query)

        sparql.setQuery(dataset_query)
        sparql.setReturnFormat(JSON)

        return(sparql.query().convert()["results"]["bindings"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")
    return {}

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}

@app.get("/get_paper_info_by_orcid")
async def get_paper_info_by_orcid(orcid: str = Query(..., description="return papers belonging to a doi")):
    data = run_sparql_query(orcid)

    if not data:
        raise HTTPException(status_code=404, detail="No dataset found with that DOI.")

    return {"orcid": orcid, "results": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)
