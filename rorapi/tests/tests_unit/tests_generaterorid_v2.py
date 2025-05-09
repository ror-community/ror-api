from django.test import SimpleTestCase
from unittest.mock import patch
from rorapi.management.commands import generaterorid
from rorapi.common.models import Errors
from rorapi.settings import ROR_API

DUPLICATE_ID_RAW = "duplicateid"
UNIQUE_ID_RAW = "uniqueid"
DUPLICATE_ROR_ID = f"{ROR_API['ID_PREFIX']}{DUPLICATE_ID_RAW}"
UNIQUE_ROR_ID = f"{ROR_API['ID_PREFIX']}{UNIQUE_ID_RAW}"
TEST_VERSION = 'v2'

class GenerateRorIdCommandTestCase(SimpleTestCase):

    @patch('rorapi.management.commands.generaterorid.get_ror_id')
    @patch('rorapi.management.commands.generaterorid.retrieve_organization')
    @patch('rorapi.management.commands.generaterorid.generate_ror_id')
    def test_check_ror_id_handles_collision_and_returns_unique(
        self, mock_generate_ror_id, mock_retrieve_organization, mock_get_ror_id
    ):
        mock_generate_ror_id.side_effect = [
            DUPLICATE_ROR_ID,
            UNIQUE_ROR_ID
        ]

        mock_get_ror_id.side_effect = lambda x: x

        mock_retrieve_organization.side_effect = [
            (None, {'id': DUPLICATE_ROR_ID, 'name': 'Mock Duplicate Org'}),
            (Errors(f"ROR ID '{UNIQUE_ROR_ID}' does not exist"), None)
        ]

        result_ror_id = generaterorid.check_ror_id(TEST_VERSION)

        self.assertEqual(result_ror_id, UNIQUE_ROR_ID)