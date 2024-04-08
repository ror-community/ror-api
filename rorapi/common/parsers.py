import jsonschema
import requests
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class JSONSchemaParser(JSONParser):

    def get_file_from_url(self, url):
        rsp = requests.get(url)
        rsp.raise_for_status()
        return rsp.json()

    def parse(self, stream, media_type=None, parser_context=None):
        schema = self.get_file_from_url("https://raw.githubusercontent.com/ror-community/ror-schema/master/ror_schema_v2_0.json")
        data = super(JSONSchemaParser, self).parse(stream, media_type,
                                                   parser_context)
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as error:
            raise ParseError(detail=error.message)
        else:
            return data