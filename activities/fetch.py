import base64
import re
import pathlib
import csv
from datetime import datetime
from typing import (
    Union,
    List,
    FrozenSet,
    Tuple,
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


class FetchError(Exception):

    def __init__(self, caused_by, context):
        self.caused_by = caused_by
        self.context = context


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
        return pd.DataFrame(columns=['author', 'timestamp', 'categories', 'sha'])


def set_cached_commit_history(repository: Repository, history: pd.DataFrame):
    cache_filename = get_cache_filepath(repository)
    cache_directory = pathlib.Path(cache_filename).parents[0]
    cache_directory.mkdir(parents=True, exist_ok=True)
    history.to_csv(get_cache_filepath(repository), index=False, quoting=csv.QUOTE_NONNUMERIC)


def is_subpath(subpath: Union[pathlib.Path, str], path: pathlib.Path) -> bool:
    return str(subpath) in [str(path)] + [str(p) for p in path.parents[:-1]]


def get_updated_tool_categories(repository: Repository, commit: Commit, status: Optional[tqdm], tool_directories: Optional[FrozenSet[str]] =None) -> Tuple[List[str], FrozenSet[str]]:
    """
    Get list of the tool categories for which tools have been added, updated, or removed.

    The function searches the filesystem tree for directories corresponding to Galaxy tools, and then checks whether any files within the determined directories have been altered.
    In case that the tool directories are known a priori, it is not necessary to search the filesystem tree.
    Using None for `tool_directories` means that the tool directories are not known a priori.
    """
    updated_tool_categories = set()

    # Fetch the directory tree if the tool directories are not known a priori
    if tool_directories is None:
        if status is not None: status.set_description_str('Fetching tree')
        tree = repository.get_git_tree(sha=commit.sha, recursive=True)
        tool_directories = frozenset([str(pathlib.Path(te.path).parents[0]) for te in tree.tree if te.path.endswith('/' + SHED_FILENAME)])

    for file in commit.files:
        for directory in pathlib.Path(file.filename).parents[:-1]:
            if str(directory) in tool_directories:
                shed_filepath = str(directory / SHED_FILENAME)
                if status is not None: status.set_description_str(f'Peeking {shed_filepath}')
                shed_file = get_string_content(repository.get_contents(shed_filepath, ref=commit.sha))
                shed_data = yaml.safe_load(shed_file)
                updated_tool_categories |= set(shed_data['categories'])
                break

    return list(sorted(updated_tool_categories)), tool_directories


def process_new_commits(repository: Repository, previous_commits: pd.DataFrame, until: Optional[datetime] =None):
    """
    Generator which yields all new commits in a repository.

    Each new commit is yielded along with the short SHA, datetime, and a tqdm object for status reporting.
    Optionally, only new commits until a specified datetime are considered.
    New commits are determined by comparing each commit to the stock of previously known commits.
    The comparison is performed using the short SHA along with the datetime of the commits.
    The stock of previously known commits is represented by a pandas dataframe, and is expected to contain at least the columns `sha` and `timestamp`, where the values in the `timestamp` column correspond to the `str` representation of the datetime of each commit.
    """
    previous_commits_set = frozenset(previous_commits[['sha', 'timestamp']].apply(tuple, axis=1).tolist())
    assert len(previous_commits) == len(previous_commits_set)
    
    get_commits_kwargs = dict(until=until) if until is not None else dict()
    commits = repository.get_commits(**get_commits_kwargs)
    new_commits_count = commits.totalCount - len(previous_commits)
    new_commits_processed = 0

    try:
        pbar = tqdm(total=new_commits_count, position=0)
        status = tqdm(total=0, bar_format='{desc}', position=1)

        for c in commits:
            if new_commits_processed >= new_commits_count: break

            short_sha = c.sha[:7]
            pbar.set_postfix_str(short_sha)
            datetime = pd.to_datetime(c.commit.author.date, utc=True)
            status.set_description_str(f'Current position: {datetime.strftime("%Y/%m/%d")}')

            if (short_sha, str(datetime)) in previous_commits_set: continue
            new_commits_processed += 1
            pbar.update(1)

            yield c, short_sha, datetime, status
    
    except Exception as ex:
        raise FetchError(caused_by=ex, context=locals())

    finally:
        pbar.close()
        status.close()


def get_commit_history(repository: Repository, until: Optional[datetime] =None) -> pd.DataFrame:
    cached_df = get_cached_commit_history(repository)
    new_entries = dict(author=list(), timestamp=list(), categories=list(), sha=list())

    # Currently known tool directories, initially unknown
    tool_directories = None

    for c, short_sha, datetime, status in process_new_commits(repository, cached_df, until):

        # If a shed file is modified, then the tool directories become unknown without further inspection
        if any([file.filename.endswith('/' + SHED_FILENAME) for file in c.files]):
            tool_directories = None

        if c.author is None:

            new_entries['author'].append('')
            new_entries['categories'].append('')

        else:

            # Get list of updated tool categories, and update the currently known tool directories
            updated_tool_categories, tool_directories = get_updated_tool_categories(repository, c, status, tool_directories)

            new_entries['author'].append(c.author.login)
            new_entries['categories'].append(','.join(updated_tool_categories))

        new_entries['timestamp'].append(str(datetime))
        new_entries['sha'].append(short_sha)

    new_entries_df = pd.DataFrame(new_entries).iloc[::-1]
    history_df = pd.concat([cached_df, new_entries_df]) if len(cached_df) > 0 else new_entries_df
    history_df.sort_values(['timestamp', 'sha'], inplace=True)
    set_cached_commit_history(repository, history_df)
    return history_df
