import base64
import re
import pathlib
import csv
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pandas as pd
import yaml

from tqdm import tqdm

from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from github.Commit import Commit
from github.GithubException import UnknownObjectException


GITHUB_URL = 'https://github.com/'
SHED_FILENAME = '.shed.yml'


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
        repo_f = repo.get_contents(f'repositories{i:02d}.list')
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


def get_cache_filepath(repository: Repository) -> str:
    return f'cache/{repository.owner.login}/{repository.name}.csv'


def get_cached_commit_history(repository: Repository) -> pd.DataFrame:
    cache_filename = get_cache_filepath(repository)
    if pathlib.Path(cache_filename).is_file():
        return pd.read_csv(cache_filename)
    else:
        return pd.DataFrame(columns=['author', 'timestamp', 'categories'])


def set_cached_commit_history(repository: Repository, history: pd.DataFrame):
    cache_filename = get_cache_filepath(repository)
    cache_directory = pathlib.Path(cache_filename).parents[0]
    cache_directory.mkdir(parents=True, exist_ok=True)
    history.to_csv(get_cache_filepath(repository), index=False, quoting=csv.QUOTE_NONNUMERIC)


def is_subpath(subpath: pathlib.Path, path: pathlib.Path) -> bool:
    return str(subpath) in [str(path)] + [str(p) for p in path.parents[:-1]]


def get_updated_tool_categories(repository: Repository, commit: Commit, pbar: tqdm) -> list:
    updated_tool_categories = set()
    tool_directories = list()
    for file in commit.files:
        updated_directories = pathlib.Path(file.filename).parents[:-1]
        if any([is_subpath(tool_directory, updated_directories[0]) for tool_directory in tool_directories]): continue
        for updated_directory in updated_directories:
            try:
                shed_filepath = str(updated_directory / SHED_FILENAME)
                pbar.set_description(f'Peeking {shed_filepath}')
                shed_file = get_string_content(repository.get_contents(shed_filepath, ref=commit.sha))
                shed_data = yaml.safe_load(shed_file)
                updated_tool_categories |= set(shed_data['categories'])
                tool_directories.append(updated_directory)
                break
            except UnknownObjectException:
                pass
    return list(updated_tool_categories)


def get_commit_history(repository: Repository) -> pd.DataFrame:
    cached_df = get_cached_commit_history(repository)
    last_cache_update = pd.to_datetime(0)
    new_entries = dict(author=list(), timestamp=list(), categories=list())
    for c in (pbar := tqdm(repository.get_commits(), total=repository.get_commits().totalCount)):
        if c.author is None: continue
        datetime = pd.to_datetime(c.last_modified)
        print(datetime)
        if datetime <= last_cache_update: break
        updated_tool_categories = get_updated_tool_categories(repository, c, pbar)
        new_entries['author'].append(c.author.login)
        new_entries['timestamp'].append(datetime)
        new_entries['categories'].append(','.join(updated_tool_categories))
        if len(new_entries['author']) > 20: break
    new_entries_df = pd.DataFrame(new_entries)
    history_df = pd.concat([cached_df, new_entries_df]) if len(cached_df) > 0 else new_entries_df
    set_cached_commit_history(repository, history_df)
    return history_df