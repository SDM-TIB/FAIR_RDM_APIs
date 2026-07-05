import logging, uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Tuple
from SPARQLWrapper import SPARQLWrapper, JSON, POST

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="Knowledge Graph Exploration API")
ENDPOINT = "https://labs.tib.eu/sdm/ldm_kg/sparql"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_sparql_client():
    s = SPARQLWrapper(ENDPOINT)
    s.setReturnFormat(JSON)
    s.setMethod(POST)
    return s


def exec_query(q: str):
    s = get_sparql_client()
    s.setQuery(q)
    return s.query().convert()["results"]["bindings"]


monovalue_set = {
    "http://purl.org/dc/terms/modified",
    "http://www.w3.org/2002/07/owl#versionInfo",
    "http://purl.org/dc/terms/license",
    "http://purl.org/dc/terms/description",
    "http://xmlns.com/foaf/0.1/page",
    "http://purl.org/dc/terms/identifier",
    "http://purl.org/dc/terms/issued",
    "http://purl.org/dc/terms/title",
    "http://purl.org/spar/datacite/usesIdentifierScheme",
    "http://www.w3.org/2006/vcard/ns#fn",
    "http://www.w3.org/2006/vcard/ns#hasEmail",
    "http://purl.org/dc/terms/accessRights",
    "http://purl.org/dc/terms/language",
    "http://purl.org/dc/terms/conformsTo",
}
prefixes = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX datacite: <http://purl.org/spar/datacite/>
PREFIX pro: <http://purl.org/spar/pro/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX schema: <http://schema.org/>
PREFIX orgk: <http://orkg.org/orkg/class/>"""

type_s, label_s, same_as_s, creator_s, dist_s, key_s, lp_s, desc_s, cit_s, pub_s = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "http://www.w3.org/2000/01/rdf-schema#label",
    "http://www.w3.org/2002/07/owl#sameAS",
    "http://purl.org/dc/terms/creator",
    "http://www.w3.org/ns/dcat#distribution",
    "http://www.w3.org/ns/dcat#keyword",
    "http://www.w3.org/ns/dcat#landingPage",
    "http://purl.org/spar/datacite/isDescribedBy",
    "http://schema.org/citation",
    "http://purl.org/dc/terms/publisher",
)


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


def _parse_o_node(o: dict) -> dict:
    return {
        "type": o["type"],
        "value": o["value"],
        **({"datatype": o["datatype"]} if "datatype" in o else {}),
    }


def _process_nested_row(row: dict, e_name: str, grouped: dict):
    grouped[row[e_name]["value"]].setdefault(row["p"]["value"], []).append(
        _parse_o_node(row["o"])
    )


def _map_bulk_prop(
    ds_uri: str, p_val: str, o_val: str, local_sets: dict, global_sets: dict
):
    m = {
        type_s: ("type_set", None),
        lp_s: ("landing_page_set", None),
        desc_s: ("is_described_by_set", None),
        cit_s: ("citation_set", None),
        creator_s: ("creator_set", "creator"),
        dist_s: ("distribution_set", "distribution"),
        pub_s: ("publisher_set", "publisher"),
        key_s: ("keyword_set", "keyword"),
    }
    if p_val in m:
        local_sets[ds_uri][m[p_val][0]].add(o_val)
        (global_sets[m[p_val][1]].add(o_val) if m[p_val][1] else None)


def _process_bulk_row(row: dict, final_res: dict, local_sets: dict, global_sets: dict):
    ds_uri, p_val = row["dataset"]["value"], row["p"]["value"]
    if ds_uri not in final_res:
        return
    if p_val in monovalue_set:
        final_res[ds_uri][p_val] = _parse_o_node(row["o"])
    else:
        _map_bulk_prop(ds_uri, p_val, row["o"]["value"], local_sets, global_sets)


def _reassemble_dataset(ds_uri: str, sets: dict, final_res: dict, nested_data: dict):
    for k, s_key in [
        (type_s, "type_set"),
        (lp_s, "landing_page_set"),
        (desc_s, "is_described_by_set"),
        (cit_s, "citation_set"),
    ]:
        if sets[s_key]:
            final_res[ds_uri][k] = list(sets[s_key])
    for k, s_key, n_key in [
        (creator_s, "creator_set", "creator"),
        (dist_s, "distribution_set", "distribution"),
        (key_s, "keyword_set", "keyword"),
        (pub_s, "publisher_set", "publisher"),
    ]:
        if sets[s_key]:
            final_res[ds_uri][k] = [
                nested_data.get(n_key, {}).get(i)
                for i in sets[s_key]
                if i in nested_data.get(n_key, {})
            ]


def _parse_author_results(results: list) -> Tuple[set, set, set]:
    return (
        set(r["author"]["value"] for r in results if "author" in r),
        set(r["dataset"]["value"] for r in results if "dataset" in r),
        set(r["same_as"]["value"] for r in results if "same_as" in r),
    )


def _inject_same_as(props: dict, orcid_data_map: dict):
    if same_as_s in props:
        props[same_as_s] = [
            {
                "uri": n["value"],
                "properties": {
                    **orcid_data_map.get(n["value"], {}),
                    type_s: orcid_data_map.get(n["value"], {}).get(
                        type_s,
                        [{"type": "uri", "value": "http://purl.org/spar/pro/Author"}],
                    ),
                },
            }
            for n in props[same_as_s]
        ]
    return props


def fetch_nested_entities(
    sparql: SPARQLWrapper, uri_set: set, e_name: str
) -> List[dict]:
    if not uri_set:
        return []
    grouped = {uri: {} for uri in uri_set}
    for row in exec_query(
        f"SELECT ?{e_name} ?p ?o WHERE {{ VALUES ?{e_name} {{ {' '.join([f'<{uri}>' for uri in uri_set])} }} ?{e_name} ?p ?o . }}"
    ):
        _process_nested_row(row, e_name, grouped)
    return [{"uri": k, "properties": v} for k, v in grouped.items()]


def get_bulk_dataset_information_helper(dataset_uris: List[str]) -> dict:
    if not dataset_uris:
        return {}
    final_results = {uri: {} for uri in dataset_uris}
    local_sets = {
        uri: {
            k: set()
            for k in [
                "type_set",
                "landing_page_set",
                "is_described_by_set",
                "citation_set",
                "creator_set",
                "distribution_set",
                "keyword_set",
                "publisher_set",
            ]
        }
        for uri in dataset_uris
    }
    global_sets = {
        k: set() for k in ["creator", "distribution", "keyword", "publisher"]
    }
    for row in exec_query(
        f"{prefixes} SELECT DISTINCT ?dataset ?p ?o WHERE {{ VALUES ?dataset {{ {' '.join([f'<{uri}>' for uri in dataset_uris])} }} ?dataset ?p ?o . }}"
    ):
        _process_bulk_row(row, final_results, local_sets, global_sets)
    nested_data = {
        entity: {
            item["uri"]: item
            for item in fetch_nested_entities(
                get_sparql_client(), global_sets[entity], entity
            )
        }
        for entity in ["creator", "distribution", "keyword", "publisher"]
        if global_sets[entity]
    }
    for ds_uri, sets in local_sets.items():
        _reassemble_dataset(ds_uri, sets, final_results, nested_data)
    return final_results


def _translate_author_to_ldm(
    items: List[str], var_name: str, match_pattern: str, formatter
) -> List[str]:
    return (
        list(
            set(
                [
                    r["author"]["value"]
                    for r in exec_query(
                        f"{prefixes} SELECT DISTINCT ?author WHERE {{ VALUES ?{var_name} {{ {' '.join([formatter(i) for i in items])} }} ?author a pro:Author ; {match_pattern} . }}"
                    )
                    if "author" in r
                ]
            )
        )
        if items
        else []
    )


def translate_orcids_to_ldm_ids(orcids: List[str]):
    return _translate_author_to_ldm(
        orcids, "orcid", "owl:sameAS ?orcid", lambda x: f"<{x}>"
    )


def translate_names_to_ldm_ids(names: List[str]):
    return _translate_author_to_ldm(
        names, "name", "rdfs:label ?name", lambda x: f'"{x}"'
    )


def translate_paper_titles_to_dois(titles: List[str]) -> List[str]:
    if not titles:
        return []
    orkg = SPARQLWrapper("https://orkg.org/sparql")
    orkg.setReturnFormat(JSON)
    orkg.setQuery(
        f"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?doi WHERE {{ VALUES ?title {{ {' '.join([f'\"{t}\"' for t in titles])} }} ?paper rdfs:label ?title . {{ ?paper <http://orkg.org/property/P26> ?doi }} UNION {{ ?paper <http://orkg.org/orkg/predicate/P26> ?doi }} UNION {{ ?paper <http://orkg.org/predicate/P26> ?doi }} }}"
    )
    try:
        return list(
            set(
                [
                    f"https://doi.org/{d}" if not d.startswith("http") else d
                    for r in orkg.query().convert()["results"]["bindings"]
                    for d in [r["doi"]["value"]]
                ]
            )
        )
    except:
        return []


def get_dataset_information_by_author_orcid_helper(x: str):
    return get_dataset_information_by_several_author_orcid_helper([x])


def get_dataset_information_by_author_ldm_id_helper(x: str):
    return get_dataset_information_by_several_author_ldm_id_helper([x])


def get_dataset_information_by_author_name_helper(x: str):
    return get_dataset_information_by_several_author_name_helper([x])


def get_dataset_information_by_paper_doi_helper(x: str):
    return get_dataset_information_by_several_paper_doi_helper([x])


def get_dataset_information_by_paper_title_helper(x: str):
    return get_dataset_information_by_several_paper_title_helper([x])


def get_dataset_information_by_dataset_doi_helper(x: str):
    return get_dataset_information_by_several_dataset_doi_helper([x])


def get_dataset_information_by_dataset_title_helper(x: str):
    return get_dataset_information_by_several_dataset_title_helper([x])


def get_dataset_information_by_dataset_ldm_id_helper(x: str):
    return get_dataset_information_by_several_dataset_ldm_id_helper([x]).get(x, {})


def get_dataset_information_by_several_author_ldm_id_helper(ids: List[str]):
    if not ids:
        return {}
    try:
        results = exec_query(
            f"{prefixes} SELECT DISTINCT ?author ?dataset ?same_as WHERE {{ VALUES ?author {{ {' '.join([f'<{u}>' for u in ids])} }} ?author a pro:Author . OPTIONAL {{ ?dataset dct:creator ?author . }} OPTIONAL {{ ?author <http://www.w3.org/2002/07/owl#sameAS> ?same_as . }} }}"
        )
        author_uris, dataset_uris, same_as_uris = _parse_author_results(results)
        final_results = {}
        final_results.update(
            get_bulk_dataset_information_helper(list(dataset_uris))
            if dataset_uris
            else {}
        )
        orcid_data_map = (
            {
                item["uri"]: item["properties"]
                for item in fetch_nested_entities(
                    get_sparql_client(), same_as_uris, "same_as_entity"
                )
            }
            if same_as_uris
            else {}
        )
        final_results.update(orcid_data_map)
        final_results.update(
            {
                author_data["uri"]: _inject_same_as(
                    author_data["properties"], orcid_data_map
                )
                for author_data in (
                    fetch_nested_entities(get_sparql_client(), author_uris, "author")
                    if author_uris
                    else []
                )
            }
        )
        return final_results
    except Exception as e:
        logger.error("SPARQL Query Failed in author LDM ID helper", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")


def get_dataset_information_by_several_author_orcid_helper(orcids: List[str]):
    return get_dataset_information_by_several_author_ldm_id_helper(
        translate_orcids_to_ldm_ids(orcids)
    )


def get_dataset_information_by_several_author_name_helper(names: List[str]):
    return get_dataset_information_by_several_author_ldm_id_helper(
        translate_names_to_ldm_ids(names)
    )


def _fetch_datasets_bulk(
    items: List[str], var_name: str, query_pattern: str, formatter
):
    if not items:
        return {}
    try:
        return get_bulk_dataset_information_helper(
            list(
                set(
                    [
                        r["dataset"]["value"]
                        for r in exec_query(
                            f"{prefixes} SELECT DISTINCT ?dataset WHERE {{ VALUES ?{var_name} {{ {' '.join([formatter(i) for i in items])} }} {query_pattern} }}"
                        )
                    ]
                )
            )
        )
    except Exception as e:
        logger.error(
            f"SPARQL Query Failed in bulk helper for {var_name}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"SPARQL Error: {str(e)}")


def get_dataset_information_by_several_paper_doi_helper(dois: List[str]):
    return _fetch_datasets_bulk(
        dois,
        "id",
        "?dataset a dcat:Dataset ; datacite:isDescribedBy ?id .",
        lambda d: f"<{d if d.startswith('http') else f'https://doi.org/{d}'}>",
    )


def get_dataset_information_by_several_paper_title_helper(titles: List[str]):
    return get_dataset_information_by_several_paper_doi_helper(
        translate_paper_titles_to_dois(titles)
    )


def get_dataset_information_by_several_dataset_doi_helper(dois: List[str]):
    return _fetch_datasets_bulk(
        dois,
        "id",
        "?dataset a dcat:Dataset ; dct:source ?id .",
        lambda d: f"<{d if d.startswith('http') else f'https://doi.org/{d}'}>",
    )


def get_dataset_information_by_several_dataset_title_helper(titles: List[str]):
    return _fetch_datasets_bulk(
        titles,
        "title",
        "?dataset a dcat:Dataset ; dct:title ?title .",
        lambda t: f'"{t}"',
    )


def get_dataset_information_by_several_dataset_ldm_id_helper(ids: List[str]):
    return get_bulk_dataset_information_helper(ids) if ids else {}


def register_api_routes(
    path: str,
    model_cls,
    list_field: str,
    param_name: str,
    single_helper,
    bulk_helper,
    is_nested_result: bool = False,
):
    @app.post(path)
    async def post_route(req: model_cls):
        items = getattr(req, list_field)
        if not items:
            raise HTTPException(400, "List cannot be empty.")
        data = bulk_helper(items)
        if not data:
            raise HTTPException(404, f"No datasets found for these {param_name}s.")
        return {
            "requested_count": len(items),
            "found_count": len(data),
            "results": data,
        }

    @app.get(path)
    async def get_route(param: str = Query(..., alias=param_name)):
        data = single_helper(param)
        if not data:
            raise HTTPException(404, f"No datasets found for this {param_name}.")
        return {
            param_name: param,
            "results": {param: data} if is_nested_result else data,
        }


register_api_routes(
    "/get_dataset_information_by_author_orcid",
    AuthorOrcidRequest,
    "author_orcids",
    "author_orcid",
    get_dataset_information_by_author_orcid_helper,
    get_dataset_information_by_several_author_orcid_helper,
)
register_api_routes(
    "/get_dataset_information_by_author_name",
    AuthorNameRequest,
    "author_names",
    "author_name",
    get_dataset_information_by_author_name_helper,
    get_dataset_information_by_several_author_name_helper,
)
register_api_routes(
    "/get_dataset_information_by_author_ldm_id",
    AuthorLdmIdRequest,
    "author_ldm_ids",
    "author_ldm_id",
    get_dataset_information_by_author_ldm_id_helper,
    get_dataset_information_by_several_author_ldm_id_helper,
)
register_api_routes(
    "/get_dataset_information_by_paper_doi",
    PaperDoiRequest,
    "paper_dois",
    "paper_doi",
    get_dataset_information_by_paper_doi_helper,
    get_dataset_information_by_several_paper_doi_helper,
)
register_api_routes(
    "/get_dataset_information_by_paper_title",
    PaperTitleRequest,
    "paper_titles",
    "paper_title",
    get_dataset_information_by_paper_title_helper,
    get_dataset_information_by_several_paper_title_helper,
)
register_api_routes(
    "/get_dataset_information_by_dataset_doi",
    DatasetDoiRequest,
    "dataset_dois",
    "dataset_doi",
    get_dataset_information_by_dataset_doi_helper,
    get_dataset_information_by_several_dataset_doi_helper,
)
register_api_routes(
    "/get_dataset_information_by_dataset_title",
    DatasetTitleRequest,
    "dataset_titles",
    "dataset_title",
    get_dataset_information_by_dataset_title_helper,
    get_dataset_information_by_several_dataset_title_helper,
)
register_api_routes(
    "/get_dataset_information_by_dataset_ldm_id",
    DatasetLdmIdRequest,
    "dataset_ldm_ids",
    "dataset_ldm_id",
    get_dataset_information_by_dataset_ldm_id_helper,
    get_dataset_information_by_several_dataset_ldm_id_helper,
    is_nested_result=True,
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5742)
