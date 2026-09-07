#! /bin/bash -xe

# Test POST
curl -X 'POST' 'http://0.0.0.0:5742/get_dataset_information_by_publisher' \
     -H 'Content-Type: application/json' \
     -d '{"publisher_ids":["https://service.tib.eu/ldmservice/organization/8802f9f3-9760-48f5-95f9-a6b3e0565205", "https://service.tib.eu/ldmservice/organization/123d6d8f-2723-4766-9181-9e9e52ab9b2b"]}'
