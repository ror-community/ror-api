import requests
import logging
from django.core.management.base import BaseCommand, CommandError
from rorapi.management.commands.deleteindex import Command as DeleteIndexCommand
from rorapi.management.commands.createindex import Command as CreateIndexCommand
from rorapi.management.commands.indexrordump import Command as IndexRorDumpCommand
from rorapi.management.commands.getrordump import Command as GetRorDumpCommand
from rorapi.settings import ROR_DUMP

REQUEST_TIMEOUT_SECONDS = 30
logger = logging.getLogger(__name__)


def build_github_headers():
    token = ROR_DUMP.get('GITHUB_TOKEN')
    if not token:
        raise CommandError('Missing GitHub authentication configuration; cannot authenticate to GitHub API.')
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }


def get_contents_url(use_test_data):
    repo_key = 'TEST_REPO_URL' if use_test_data else 'PROD_REPO_URL'
    repo_url = ROR_DUMP.get(repo_key)
    if not repo_url:
        raise CommandError('Repository source URL is not configured; cannot build contents endpoint.')
    return f"{repo_url.rstrip('/')}/contents"


def get_ror_dump_sha(filename, use_test_data):
    headers = build_github_headers()
    contents_url = get_contents_url(use_test_data)

    try:
        response = requests.get(contents_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout as exc:
        raise CommandError(f'Request timed out while reaching {contents_url}.') from exc
    except requests.exceptions.ConnectionError as exc:
        raise CommandError(f'Could not connect to {contents_url}.') from exc
    except requests.exceptions.RequestException as exc:
        raise CommandError(f'GitHub request failed for {contents_url}: {exc}') from exc

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status = response.status_code
        if status in (401, 403):
            raise CommandError('GitHub authentication/authorization failed. Check API credentials and permissions.') from exc
        if status == 404:
            raise CommandError(f'GitHub repository contents endpoint not found: {contents_url}.') from exc
        raise CommandError(f'GitHub API returned HTTP {status} for {contents_url}.') from exc

    try:
        repo_contents = response.json()
    except ValueError as exc:
        raise CommandError(f'GitHub API returned invalid JSON for {contents_url}.') from exc

    if not isinstance(repo_contents, list):
        raise CommandError(f'Unexpected GitHub API response type for {contents_url}: {type(repo_contents).__name__}.')

    for entry in repo_contents:
        if not isinstance(entry, dict):
            continue
        name = entry.get('name')
        sha = entry.get('sha')
        if not name or not sha:
            continue
        if filename in name:
            return sha

    return None


class Command(BaseCommand):
    help = 'Setup ROR API'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='Name of data dump zip file to index without extension')
        parser.add_argument('-s', '--schema', type=int, choices=[2], default=2, help='Schema version to index (v2 only)')
        parser.add_argument('-t', '--testdata', action='store_true', help='Set flag to pull data dump from ror-data-test instead of ror-data')

    def handle(self, *args, **options):
        msg = None
        # make sure ROR dump file exists
        filename = options['filename']
        use_test_data = options['testdata']
        if use_test_data:
            print("Using ror-data-test repo")
        else:
            print("Using ror-data repo")

        try:
            sha = get_ror_dump_sha(filename, use_test_data)
        except CommandError as exc:
            msg = f'ERROR: Could not validate ROR data dump source. {exc}'
            self.stdout.write(msg)
            return msg

        if sha:
            try:
                GetRorDumpCommand().handle(*args, **options)
                DeleteIndexCommand().handle(*args, **options)
                CreateIndexCommand().handle(*args, **options)
                IndexRorDumpCommand().handle(*args, **options)
                msg = 'SUCCESS: ROR dataset {} indexed in v2. Using test repo: {}'.format(filename, str(use_test_data))
            except Exception:
                logger.exception('Failed while indexing ROR dataset %s (use_test_data=%s).', filename, use_test_data)
                msg = 'ERROR: Could not index ROR data dump. Check API logs for details.'
        else:
            msg = 'ERROR: ROR dataset for file {} not found. '.format(filename) \
                + 'Please generate the data dump first.'
            self.stdout.write(msg)

        return msg

