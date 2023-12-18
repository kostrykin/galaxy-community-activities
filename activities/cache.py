import pathlib
import csv
import glob
import re

import pandas as pd
from github.Repository import Repository
from typing import (
    List,
    Union,
)


def get_cached_repository_filepath(repository: Union[str, Repository]) -> str:
    repo = repository if isinstance(repository, str) else f'{repository.owner.login}/{repository.name}'
    return f'cache/repositories/{repo}.csv'


def get_cached_authors_filepath() -> str:
    return f'cache/authors.csv'


def get_cached_commit_history(repository: Repository) -> pd.DataFrame:
    cache_filename = get_cached_repository_filepath(repository)
    if pathlib.Path(cache_filename).is_file():
        return pd.read_csv(cache_filename)
    else:
        return pd.DataFrame(columns=['author', 'timestamp', 'categories', 'sha'])


def set_cached_commit_history(repository: Repository, history: pd.DataFrame):
    cache_filename = get_cached_repository_filepath(repository)
    cache_directory = pathlib.Path(cache_filename).parents[0]
    cache_directory.mkdir(parents=True, exist_ok=True)
    history.to_csv(cache_filename, index=False, quoting=csv.QUOTE_NONNUMERIC)


def get_cached_authors() -> pd.DataFrame:
    cache_filename = get_cached_authors_filepath()
    if pathlib.Path(cache_filename).is_file():
        df = pd.read_csv(cache_filename)
        df['avatar_url'] = df['avatar_url'].fillna('')
        return df
    else:
        return pd.DataFrame(columns=['username', 'avatar_url', 'timestamp'])


def set_cached_authors(authors: pd.DataFrame):
    cache_filename = get_cached_authors_filepath()
    cache_directory = pathlib.Path(cache_filename).parents[0]
    cache_directory.mkdir(parents=True, exist_ok=True)
    authors.to_csv(cache_filename, index=False, quoting=csv.QUOTE_NONNUMERIC)


def get_cached_repositories() -> List[str]:
    repositories = list()
    for cache_filepath in glob.glob('cache/repositories/*/*.csv'):
        match = re.match(r'^cache/repositories/(.*).csv$', cache_filepath)
        repositories.append(match.group(1))
    return repositories
