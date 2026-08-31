#! /bin/bash -xe

curl -X 'POST' 'http://0.0.0.0:5742/get_dataset_information_by_keyword' \
     -H 'Content-Type: application/json' \
     -d '{"keywords":["FT","cc"]}'
