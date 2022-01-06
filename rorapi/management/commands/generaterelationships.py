import json
import os
from os.path import exists
import logging
import requests 
from csv import DictReader
import re

logging.basicConfig(filename='errors.log',level=logging.ERROR)
FILE = "test_file.csv"
API_URL = "http://api.ror.org/organizations/"
def read_relshp():
    relation = []
    rel_dict = {}
    try:
        with open(FILE, 'r') as rel:
            relationships = DictReader(rel)
            for row in relationships:
                check_record_id = parse_record_id(row['Record ID'])
                check_related_id = parse_record_id(row['Related ID'])
                if (check_record_id and check_related_id): 
                    rel_dict['short_record_id'] = check_record_id
                    rel_dict['short_related_id'] = check_related_id
                    rel_dict['record_name'] = row['Name of org in Record ID']
                    rel_dict['record_id'] = row['Record ID']
                    rel_dict['related_id'] = row['Related ID']
                    rel_dict['related_name'] = row['Name of org in Related ID']
                    rel_dict['record_relationship'] = row['Relationship of Record ID to Related ID']
                    rel_dict['related_location'] = row['Current location of Related ID']
                    relation.append(rel_dict.copy())
    except IOError as e:
        logging.error(f"Reading file {FILE}: {e}")
    return relation

def check_file(file=FILE):
    file_exists = True
    if not(exists(file)):
        logging.error(f"{file} must exist")
        file_exists = False 
    return file_exists 

def parse_record_id(id):
    parsed_id = None
    pattern = '^https:\/\/ror.org\/(0[a-x|0-9]{8})$'
    ror_id = re.search(pattern, id)
    if ror_id:
        parsed_id = ror_id.group(1)
    else:
        logging.error(f"ROR ID: {id} does not match format: {pattern}")
    return parsed_id

def get_record(id, filename):
    download_url=API_URL + id
    try:
        rsp = requests.get(download_url)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request for {download_url}: {e}")
    try:
        with open(filename, "w") as record:
            record.write(rsp.text)
    except Exception as e:
        logging.error(f"Writing {filename}: e")

def download_record(records):
    # download all records that are labeled as in production
    for r in records:
        if (r['related_location'] == "Production"):
            filename = r['short_related_id'] + ".json"
            if not(check_file(filename)):
                get_record(r['short_related_id'], filename)

def remove_bad_records(records, bad_records):
    updated_records = [r for r in records if not(r['short_record_id'] in bad_records or r['short_related_id'] in bad_records)]
    return updated_records
   
def check_record_files(records):
    bad_records = []
    for r in records:
        filename = r['short_record_id'] + ".json"
        if not(check_file(filename)):
            bad_records.append(r['short_record_id'])
            logging.error(f"Record: {r['record_id']} will not be processed because {filename} does not exist.")

    if len(bad_records) > 0:
        #remove dupes
        bad_records = list(dict.fromkeys(bad_records))
        records = remove_bad_records(records, bad_records)

    return records

def process_records(records):
    download_record(records)
    recs = check_record_files(records)

def generate_relationships():
    if check_file():
        rel = read_relshp()
        if rel:
            process_records(rel)
        else:
            print("womp! womp!")
        

def main():
    generate_relationships()

if __name__ == "__main__":
    main()
