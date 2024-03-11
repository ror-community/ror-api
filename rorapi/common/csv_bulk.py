import csv
import json
import io
import os
import shutil
import urllib
from datetime import datetime
from rest_framework.renderers import JSONRenderer
from rorapi.settings import DATA
from rorapi.v2.serializers import (
    OrganizationSerializer as OrganizationSerializerV2
)
from rorapi.common.csv_update import update_record_from_csv
from rorapi.common.csv_create import new_record_from_csv


def save_record_file(ror_id, updated, json_obj, dir_name):
    dir_path = os.path.join(DATA['DIR'],dir_name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    subdir = 'updates' if updated else 'new'
    if not os.path.exists(os.path.join(dir_path, subdir)):
        os.mkdir(os.path.join(dir_path, subdir))
    full_path = os.path.join(dir_path, subdir, ror_id.split('https://ror.org/')[1] + '.json')
    with open(full_path, "w") as outfile:
        json.dump(json_obj, outfile, ensure_ascii=False, indent=2)

def save_report_file(report, report_fields, csv_file, dir_name):
    dir_path = os.path.join(DATA['DIR'],dir_name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
    filepath =  os.path.join(dir_path, 'report.csv')
    with open(filepath, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=report_fields)
            writer.writeheader()
            writer.writerows(report)
    # save copy of input file
    filepath =  os.path.join(dir_path, 'input.csv')
    csv_file.seek(0)
    with open(filepath, 'wb+') as f:
        for chunk in csv_file.chunks():
            f.write(chunk)

def process_csv(csv_file, version):
    print("Processing CSV")
    dir_name = datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + "-ror-records"
    success_msg = None
    error = None
    report = []
    report_fields = ['row', 'ror_id', 'action', 'errors']
    skipped_count = 0
    updated_count = 0
    new_count = 0
    read_file = csv_file.read().decode('utf-8')
    print(read_file)
    reader = csv.DictReader(io.StringIO(read_file))
    row_num = 2
    for row in reader:
        ror_id = None
        updated = False
        print("Row data")
        print(row)
        if row['id']:
            ror_id = row['id']
            updated = True
            row_errors, v2_record = update_record_from_csv(row, version)
        else:
            row_errors, v2_record = new_record_from_csv(row, version)
        if not row_errors:
            if updated:
                action = 'updated'
                updated_count += 1
            else:
                action = 'created'
                new_count += 1
            ror_id = v2_record['id']
            serializer = OrganizationSerializerV2(v2_record)
            json_obj = json.loads(JSONRenderer().render(serializer.data))
            print(json_obj)
            #create file
            file = save_record_file(ror_id, updated, json_obj, dir_name)
        else:
            action = 'skipped'
            skipped_count += 1
        report.append({"row": row_num, "ror_id": ror_id if ror_id else '', "action": action, "errors": "; ".join(row_errors) if row_errors else ''})
        row_num += 1
    if new_count > 0 or updated_count > 0 or skipped_count > 0:
        try:
            #create report file
            save_report_file(report, report_fields, csv_file, dir_name)
            # create zip file
            zipfile = shutil.make_archive(os.path.join(DATA['DIR'], dir_name), 'zip', DATA['DIR'], dir_name)
            # upload to S3
            try:
                DATA['CLIENT'].upload_file(zipfile, DATA['PUBLIC_STORE'], dir_name + '.zip')
                zipfile = f"https://s3.eu-west-1.amazonaws.com/{DATA['PUBLIC_STORE']}/{urllib.parse.quote(dir_name)}.zip"
            except Exception as e:
                error = f"Error uploading zipfile to S3: {e}"
        except Exception as e:
            error = f"Unexpected error generating records: {e}"
    success_msg = {"file": zipfile,
                   "rows processed": new_count + updated_count + skipped_count,
                   "created": new_count,
                   "udpated": updated_count,
                   "skipped": skipped_count}
    return error, success_msg