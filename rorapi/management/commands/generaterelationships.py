import json
import os
import logging
import requests
from csv import DictReader
import re
import sys
import update_address as ua

ERROR_LOG = "relationship_errors.log"
logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')
API_URL = "http://api.ror.org/organizations/"
UPDATED_RECORDS_PATH = "updates/"

def read_relshp(file):
    print("PROCESSING CSV")
    relation = []
    rel_dict = {}
    row_count = 0
    relationship_count = 0
    try:
        with open(file, 'r') as rel:
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
                    rel_dict['record_relationship'] = row['Relationship of Related ID to Record ID'].title()
                    rel_dict['related_location'] = row['Current location of Related ID'].title()
                    relation.append(rel_dict.copy())
                    relationship_count += 1
                row_count += 1
        print(str(row_count)+ " rows found")
        print(str(relationship_count)+ " valid relationships found")
    except IOError as e:
        logging.error(f"Reading file {file}: {e}")
    return relation

def check_file(file):
    filepath = ''
    for root, dirs, files in os.walk(".", topdown=True):
        if file in files:
            filepath = (os.path.join(root, file))
    return filepath

def parse_record_id(id):
    parsed_id = None
    pattern = '^https:\/\/ror.org\/(0[a-z|0-9]{8})$'
    ror_id = re.search(pattern, id)
    if ror_id:
        parsed_id = ror_id.group(1)
    else:
        logging.error(f"ROR ID: {id} does not match format: {pattern}. Record will not be processed")
    return parsed_id

def get_record(id, filename):
    download_url=API_URL + id
    try:
        rsp = requests.get(download_url)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request for {download_url}: {e}")

    try:
        response = rsp.json()
        updated_record = ua.update_geonames(response)
        with open(UPDATED_RECORDS_PATH + filename, "w", encoding='utf8') as f:
            json.dump(updated_record, f,  ensure_ascii=False)
    except Exception as e:
        logging.error(f"Writing {filename}: {e}")

def download_record(records):
    print("DOWNLOADING PRODUCTION RECORDS")
    downloaded_records_count = 0
    if not os.path.exists(UPDATED_RECORDS_PATH):
        os.makedirs(UPDATED_RECORDS_PATH)
    # download all records that are labeled as in production
    for r in records:
        if (r['related_location'] == "Production"):
            filename = r['short_related_id'] + ".json"
            if not(check_file(filename)):
                get_record(r['short_related_id'], filename)
                downloaded_records_count += 1
    print(str(downloaded_records_count) + " records downloaded")

def remove_bad_records(records, bad_records):
    updated_records = [r for r in records if not(r['short_record_id'] in bad_records or r['short_related_id'] in bad_records)]
    print (str(len(bad_records)) + " bad records removed")
    return updated_records

def check_record_files(records):
    print ("CHECKING FOR MISSING RECORDS")
    bad_records = []
    for r in records:
        filename = r['short_record_id'] + ".json"
        if not check_file(filename):
            bad_records.append(r['short_record_id'])
            logging.error(f"Record: {r['record_id']} will not be processed because {filename} does not exist.")

    for i in range(len(records)):
        if records[i]['short_related_id'] in bad_records:
            logging.error(f"Record {records[i]['short_record_id']} will not contain a relationship for {records[i]['short_related_id']} because {records[i]['short_related_id']}.json does not exist")

    if len(bad_records) > 0:
        #remove dupes
        bad_records = list(dict.fromkeys(bad_records))
        records = remove_bad_records(records, bad_records)
    return records

def check_relationship(former_relationship, current_relationship_id):
    return [r for r in former_relationship if not(r['id'] == current_relationship_id)]

def get_related_name(related_id):
    filename = related_id + ".json"
    filepath = check_file(filename)
    name = None
    try:
        with open(filepath, 'r') as f:
            file_data = json.load(f)
            name = file_data['name']
    except Exception as e:
        logging.error(f"Reading {filepath}: {e}")
    return name

def process_one_record(record):
    filename = record['short_record_id'] + ".json"
    filepath = check_file(filename)
    relationship = {
        "label": get_related_name(record['short_related_id']),
        "type": record['record_relationship'],
        "id": record['related_id']
    }
    try:
        with open(filepath, 'r+') as f:
            file_data = json.load(f)
            file_data['relationships'] = check_relationship(file_data['relationships'], record['related_id'])
            file_data['relationships'].append(relationship.copy())
            f.seek(0)
            json.dump(file_data, f, ensure_ascii=False, indent=2)
            f.truncate()
    except Exception as e:
        logging.error(f"Writing {filepath}: {e}")

def process_records(records):
    print("PROCESSING RECORDS")
    processed_records_count = 0
    for r in records:
        process_one_record(r)
        processed_records_count += 1
    print(str(processed_records_count) + " records updated")

def generate_relationships(file):
    if check_file(file):
        rel = read_relshp(file)
        if rel:
            download_record(rel)
            updated_recs = check_record_files(rel)
            process_records(updated_recs)
        else:
            logging.error(f"No relationships found in {file}")
    else:
        logging.error(f"{file} must exist to process relationship records")

def main():
    file = sys.argv[1]
    generate_relationships(file)
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN relationship_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()
