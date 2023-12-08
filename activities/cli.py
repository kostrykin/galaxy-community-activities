import argparse
import os
import sys
import string
import random
import dill

from . import fetch

assert sys.version_info >= (3, 10)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--api', help='GitHub access token', default=None)
    parser.add_argument('--repo', help='Run for a single repository (owner/name)', default=None)
    parser.add_argument('--verbose', action='store_true', default=False)
    parser.add_argument('--until', type=int, help='Only consider commits until the given year', default=None)
    args = parser.parse_args()

    if args.api is None:
        args.api = os.environ.get('GITHUB_TOKEN')

    g = fetch.Github(args.api)

    until = fetch.datetime(year=args.until, month=12, day=31, hour=23, minute=59, second=59) if args.until is not None else None

    try:
        if args.repo is None:
            repositories = fetch.get_tool_github_repositories(g)
        else:
            repositories = [f'{fetch.GITHUB_URL}{args.repo}']
        
        for repository_url in repositories:
            print(f'\n{repository_url} ↴')
            repo = fetch.get_github_repository(g, repository_url)
            fetch.get_commit_history(repo, until, args.verbose)

    except fetch.FetchError as ex:
        suid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        dump_filename = f'.dump-{suid}.dill'
        print(f'Dumping context info to: {dump_filename}')
        with open(dump_filename, 'wb') as fp:
            dill.dump(ex.context, fp, byref=True)
        raise ex.caused_by
