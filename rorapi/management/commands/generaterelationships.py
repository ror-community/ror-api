import json
import os
from os.path import exists
import logging
import requests 
from csv import DictReader
import re

logging.basicConfig(filename='errors.log',level=logging.ERROR)
FILE = "t.csv"
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
                    rel_dict['record_name'] = row['Name of org in Record ID']
                    rel_dict['record_id'] = row['Record ID']
                    rel_dict['related_id'] = row['Related ID']
                    rel_dict['related_name'] = row['Name of org in Related ID']
                    rel_dict['record_relationship'] = row['Relationship of Record ID to Related ID']
                    rel_dict['related_location'] = row['Current location of Related ID']
                    relation.append(rel_dict)
    except Exception as e:
        logging.error(f"ERROR reading file {FILE}: {e}")
    return relation

def parse_record_id(id):
    parsed_id = None
    pattern = '^https:\/\/ror.org\/(0[a-x|0-9]{8})$'
    ror_id = re.search(pattern, id)
    if ror_id:
        parsed_id = ror_id.group(1)
    else:
        logging.error(f"ROR ID: {id} does not match format: {pattern}")
    return parsed_id

def check_file():
    file_exists = True
    if not(exists(FILE)):
        logging.error(f"{FILE} must exist")
        file_exists = False 
    return file_exists 

def generate_relationships():
    if check_file():
        rel = read_relshp()
        if rel:
            print("heya")
        else:
            print("womp! womp!")
        

def main():
    generate_relationships()

if __name__ == "__main__":
    main()
