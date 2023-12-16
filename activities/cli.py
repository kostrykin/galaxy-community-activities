import argparse
import os
import sys
from typing import (
    List,
)

from . import fetch

assert sys.version_info >= (3, 10)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--api', help='GitHub access token', default=None)
    parser.add_argument('--repo', help='Run for a single repository (owner/name)', default=None)
    parser.add_argument('--until', type=int, help='Only consider commits until the given year', default=None)
    parser.add_argument('--list', help='List available repostiries', action='store_true', default=False)
    args = parser.parse_args()

    if args.api is None:
        args.api = os.environ.get('GITHUB_TOKEN')

    g: fetch.Github = fetch.Github(args.api)
    until = fetch.datetime(year=args.until, month=12, day=31, hour=23, minute=59, second=59) if args.until is not None else None

    # Get list of repositories
    repositories: List[fetch.RepositoryInfo] = fetch.get_github_repositories(g)

    # Apply repository filter
    if args.repo is not None:
        repositories = [rinfo for rinfo in repositories if rinfo.url == f'{fetch.GITHUB_URL}{args.repo}']

    if args.list:
        print('\n'.join([f'- {rinfo.url}' for rinfo in repositories]))
    else:
        for ridx, rinfo in enumerate(repositories):
            print(f'\n({ridx + 1}/{len(repositories)}) {rinfo.url} ↴')
            fetch.get_commit_history(g, rinfo, until)
