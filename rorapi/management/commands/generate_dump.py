import argparse
import json
import os
import logging
import sys
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime

NOW = datetime.now()
ERROR_LOG = "errors.log"
INPUT_PATH = "./"
OUTPUT_PATH = "./"
TEMP_NEW_UPDATED_RECORDS_CONCAT = "temp-updated-records.json"
TEMP_DUMP_UPDATED_RECORDS_REMOVED = "temp-dump-updated-records-removed.json"
NEW_DUMP_SUFFIX = "-" + NOW.strftime("%Y-%m-%d") + "-ror-data"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def concat_files(filepath):
    updated_count = 0
    updated_record_ids = []
    updated_records = []
    files = [os.path.join(filepath, file) for file in os.listdir(filepath) if file.endswith('.json')]
    try:
        for f in files:
            with open(f) as infile:
                file_data = json.load(infile)
                updated_records.append(file_data)
                ror_id = file_data['id']
                updated_record_ids.append(ror_id)
            updated_count += 1
        open(INPUT_PATH + TEMP_NEW_UPDATED_RECORDS_CONCAT, "w").write(
            json.dumps(updated_records, indent=4, separators=(',', ': '))
        )
    except Exception as e:
        logging.error(f"Error concatenating files: {e}")

    print(str(updated_count) + " new/updated records found")
    print(updated_record_ids)
    return updated_record_ids

def remove_existing_records(ror_ids, existing_dump_zip_path):
    existing_dump_unzipped = ''
    indexes = []
    records_to_remove = []
    with ZipFile(existing_dump_zip_path, "r") as zf:
        if len(zf.namelist())==1:
            for name in zf.namelist():
                # assumes ror-data zip will only contain 1 file
                existing_dump_unzipped = zf.extract(name, INPUT_PATH)
        else:
            print("Dump zip contains multiple files. Something is wrong.")
    try:
        f = open(existing_dump_unzipped, 'r')
        json_data = json.load(f)
        for i in range(len(json_data)):
            for ror_id in ror_ids:
                if(json_data[i]["id"] == ror_id):
                    indexes.append(i)
                    records_to_remove.append(ror_id)
                    break

        print(str(len(json_data)) + " records in existing dump " + existing_dump_unzipped)
        print(str(len(records_to_remove)) + " records to remove")
        print(records_to_remove)
        for index in sorted(indexes, reverse=True):
            del json_data[index]
        open(INPUT_PATH + TEMP_DUMP_UPDATED_RECORDS_REMOVED, "w").write(
            json.dumps(json_data, indent=4, separators=(',', ': '))
        )
    except Exception as e:
        logging.error("Error removing existing records: {e}")

def create_new_dump(release_name):
    temp_dump_updated_records_removed = open(INPUT_PATH + TEMP_DUMP_UPDATED_RECORDS_REMOVED, 'r')
    temp_dump_updated_records_removed_json = json.load(temp_dump_updated_records_removed)
    updated_records = open(INPUT_PATH + TEMP_NEW_UPDATED_RECORDS_CONCAT, 'r')
    updated_records_json = json.load(updated_records)
    print(str(len(updated_records_json)) + " records adding to dump")
    try:
        for i in updated_records_json:
            temp_dump_updated_records_removed_json.append(i)
        print(str(len(temp_dump_updated_records_removed_json)) + " records in new dump")
        open(INPUT_PATH + release_name + NEW_DUMP_SUFFIX + ".json", "w").write(
            json.dumps(temp_dump_updated_records_removed_json, indent=4, separators=(',', ': '))
        )
        with ZipFile(OUTPUT_PATH + release_name + NEW_DUMP_SUFFIX + ".zip", 'w', ZIP_DEFLATED) as myzip:
            myzip.write(INPUT_PATH + release_name + NEW_DUMP_SUFFIX + ".json")
    except Exception as e:
        logging.error("Error creating new dump: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--releasedirname', type=str)
    parser.add_argument('-e', '--existingdumpname', type=str)
    args = parser.parse_args()
    input_dir = INPUT_PATH + args.releasedirname + "/"
    existing_dump_zip_path = OUTPUT_PATH + args.existingdumpname + ".zip"
    if os.path.exists(input_dir):
        updated_record_ids = concat_files(input_dir)
        remove_existing_records(updated_record_ids, existing_dump_zip_path)
        create_new_dump(args.releasedirname)
    else:
        print("File " + input_dir + " does not exist. Cannot process files.")

    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()