# Knowledge Graph Exploration API Reference

The Knowledge Graph Exploration API is a FastAPI-based service designed to query and retrieve dataset metadata from a SPARQL-enabled knowledge graph. It allows users to extract dataset information by associating it with specific authors (via ORCID, Name, or LDM ID), academic papers (via DOI or Title), or directly querying dataset identifiers.

---

## 1. Setup and Execution

### Requirements
The API requires Python and the following dependencies (as defined in `requirements.txt`):
*   `fastapi`
*   `uvicorn`
*   `SPARQLWrapper`

### Installation
Install the required packages using standard Python package management:
```sh
pip install -r requirements.txt
```

### Running the Server
The API runs on port `5742` by default. You can start the server directly through the Python script:
```sh
python api.py
```
*Note: The API is configured to query a local SPARQL endpoint (`http://127.0.0.1:8890/sparql/`) by default. To connect to the production Leibniz Data Manager (LDM), update the `ENDPOINT` variable in `api.py` to `https://labs.tib.eu/sdm/ldm_kg/sparql`.*

---

## 2. Core Behavior

*   **GET Requests:** Used for querying a single entity. The parameter is passed in the URL query string.
*   **POST Requests:** Used for querying multiple entities in bulk. The payload must be a JSON object containing a list of strings.
*   **Response Structure:** Successful queries return a JSON object detailing the requested identifier, the number of found results (for POST requests), and a `results` dictionary mapping the entity URIs to their flattened RDF properties.
*   **Error Handling:**
    *   Returns `404 Not Found` if no datasets match the query.
    *   Returns `400 Bad Request` if a POST request submits an empty list.
    *   Returns `500 Internal Server Error` if the underlying SPARQL query fails.

---

## 3. Endpoint Reference

### Author Endpoints
Retrieve datasets associated with a specific author.

| Method | Endpoint | Payload / Query Parameter |
| :--- | :--- | :--- |
| **GET** | `/get_dataset_information_by_author_orcid` | `?author_orcid=<string>` |
| **POST** | `/get_dataset_information_by_author_orcid` | `{"author_orcids": ["<string>"]}` |
| **GET** | `/get_dataset_information_by_author_name` | `?author_name=<string>` |
| **POST** | `/get_dataset_information_by_author_name` | `{"author_names": ["<string>"]}` |
| **GET** | `/get_dataset_information_by_author_ldm_id` | `?author_ldm_id=<string>` |
| **POST** | `/get_dataset_information_by_author_ldm_id` | `{"author_ldm_ids": ["<string>"]}` |

**Example GET Request (Author Name):**
```sh
curl -X GET "http://0.0.0.0:5742/get_dataset_information_by_author_name?author_name=Maria-Esther%20Vidal"
```

**Example POST Request (Author ORCID):**
```sh
curl -X POST "http://0.0.0.0:5742/get_dataset_information_by_author_orcid" -H "Content-Type: application/json" -d '{"author_orcids": ["https://orcid.org/0000-0003-1160-8727", "https://orcid.org/0000-0002-9835-4354"]}'
```

### Paper Endpoints
Retrieve datasets described by or associated with specific research papers.

| Method | Endpoint | Payload / Query Parameter |
| :--- | :--- | :--- |
| **GET** | `/get_dataset_information_by_paper_doi` | `?paper_doi=<string>` |
| **POST** | `/get_dataset_information_by_paper_doi` | `{"paper_dois": ["<string>"]}` |
| **GET** | `/get_dataset_information_by_paper_title` | `?paper_title=<string>` |
| **POST** | `/get_dataset_information_by_paper_title` | `{"paper_titles": ["<string>"]}` |

**Example GET Request (Paper Title):**
```sh
curl -X GET "http://0.0.0.0:5742/get_dataset_information_by_paper_title?paper_title=Statistical%20predicate%20invention"
```

**Example POST Request (Paper DOI):**
```sh
curl -X POST "http://0.0.0.0:5742/get_dataset_information_by_paper_doi" -H "Content-Type: application/json" -d '{"paper_dois": ["http://orkg.org/orkg/resource/R576987", "https://doi.org/10.1016/j.websem.2005.06.005"]}'
```

### Dataset Endpoints
Retrieve metadata for datasets directly via their identifiers.

| Method | Endpoint | Payload / Query Parameter |
| :--- | :--- | :--- |
| **GET** | `/get_dataset_information_by_dataset_doi` | `?dataset_doi=<string>` |
| **POST** | `/get_dataset_information_by_dataset_doi` | `{"dataset_dois": ["<string>"]}` |
| **GET** | `/get_dataset_information_by_dataset_title` | `?dataset_title=<string>` |
| **POST** | `/get_dataset_information_by_dataset_title` | `{"dataset_titles": ["<string>"]}` |
| **GET** | `/get_dataset_information_by_dataset_ldm_id` | `?dataset_ldm_id=<string>` |
| **POST** | `/get_dataset_information_by_dataset_ldm_id` | `{"dataset_ldm_ids": ["<string>"]}` |

**Example GET Request (Dataset DOI):**
```sh
curl -X GET "http://0.0.0.0:5742/get_dataset_information_by_dataset_doi?dataset_doi=https://doi.org/10.1594/PANGAEA.804388"
```

**Example POST Request (Dataset LDM ID):**
```sh
curl -X POST "http://0.0.0.0:5742/get_dataset_information_by_dataset_ldm_id" -H "Content-Type: application/json" -d '{"dataset_ldm_ids": ["https://research.tib.eu/ldm/00023be0-7b88-4bed-9805-21259c5f2bc2", "https://research.tib.eu/ldm/00033075-0c3e-471a-a95a-f8cb52c221b5"]}'
```

---

## 4. Standard Response Payload

A successful query returns a flattened dictionary of graph properties. Each object inside `results` is keyed by its URI. Monovalue attributes are returned as objects mapping type to value, while complex properties (creators, distributions, keywords) are grouped into arrays.

**Example JSON Output (POST Method):**
```json
{
  "requested_count": 2,
  "found_count": 2,
  "results": {
    "https://research.tib.eu/ldm/00023be0-7b88-4bed-9805-21259c5f2bc2": {
      "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": [
        "http://www.w3.org/ns/dcat#Dataset"
      ],
      "http://purl.org/dc/terms/title": {
        "type": "literal",
        "value": "Hydrochemistry measured on water bottle samples during Le Suroît cruise DYNAPROC"
      },
      "http://purl.org/dc/terms/creator": [
        {
          "uri": "https://research.tib.eu/ldm/6",
          "properties": {
             "http://www.w3.org/2000/01/rdf-schema#label": {
               "type": "literal",
               "value": "Maria-Esther Vidal"
             }
          }
        }
      ]
    }
  }
}
```
