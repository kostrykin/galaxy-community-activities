import base64
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd

from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository


GITHUB_URL = 'https://github.com/'


def get_string_content(cf: ContentFile) -> str:
    """
    Get string of the content from a ContentFile

    Source from: https://github.com/galaxyproject/galaxy_tool_metadata_extractor/blob/41c3514e3a94f6c4b392cafb38042650355aba20/bin/extract_galaxy_tools.py

    :param cf: GitHub ContentFile object
    """
    return base64.b64decode(cf.content).decode('utf-8')


def get_tool_github_repositories(g: Github) -> List[str]:
    """
    Get list of tool GitHub repositories to parse

    Source from: https://github.com/galaxyproject/galaxy_tool_metadata_extractor/blob/41c3514e3a94f6c4b392cafb38042650355aba20/bin/extract_galaxy_tools.py

    :param g: GitHub instance
    """
    repo = g.get_user('galaxyproject').get_repo('planemo-monitor')
    repo_list: List[str] = []
    for i in range(1, 5):
        repo_f = repo.get_contents(f'repositories0{i}.list')
        repo_l = get_string_content(repo_f).rstrip()
        repo_list.extend(repo_l.split('\n'))
    return repo_list


def get_github_repository(g: Github, repository_url: str) -> Repository:
    assert repository_url.lower().startswith(GITHUB_URL.lower()), f'Invalid URL: {repository_url}'
    repository_url = repository_url[len(GITHUB_URL):]
    repository_url_match = re.match(r'^([^/]+)/([^/]+)/?$', repository_url)
    assert repository_url_match is not None, f'Invalid URL pattern: {repository_url}'
    owner = repository_url_match.group(1)
    name = repository_url_match.group(2)
    return g.get_repo(f'{owner}/{name}')


def get_cached_commit_history(repository: Repository) -> pd.DataFrame:
    return pd.DataFrame(columns=['author', 'timestamp'])


def set_cached_commit_history(repository: Repository, history: pd.DataFrame):
    pass


def get_commit_history(repository: Repository) -> pd.DataFrame:
    cached_df = get_cached_commit_history(repository)
    last_cache_update = pd.to_datetime(0)
    new_entries = dict(author=list(), timestamp=list())
    for c in repository.get_commits():
        if c.author is None: continue
        datetime = pd.to_datetime(c.last_modified)
        if datetime <= last_cache_update: break
        new_entries['author'].append(c.author.login)
        new_entries['timestamps'].append(datetime)
    new_entries_df = pd.DataFrame(new_entries)
    history_df = pd.concat([cached_df, new_entries_df])
    set_cached_commit_history(repository, history_df)
    return history_df