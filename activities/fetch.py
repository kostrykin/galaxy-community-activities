from . import cache

import base64
import re
import pathlib
import csv
import json
import urllib.request
import collections
import random
import warnings
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Union,
    List,
    FrozenSet,
    Set,
    Tuple,
    Optional,
    Callable,
)

import pandas as pd
import yaml

from tqdm import tqdm

from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from github.Commit import Commit
from github.GithubException import (
    IncompletableObject,
    UnknownObjectException,
)


GITHUB_URL = 'https://github.com/'
GITHUB_REPOSITORY_PATTERN = r'^([^/]+)/([^/]+)/?$'
SHED_FILENAME = '.shed.yml'


def get_string_content(cf: ContentFile) -> str:
    """
    Get string of the content from a ContentFile

    Source from: https://github.com/galaxyproject/galaxy_tool_metadata_extractor/blob/41c3514e3a94f6c4b392cafb38042650355aba20/bin/extract_galaxy_tools.py

    :param cf: GitHub ContentFile object
    """
    return base64.b64decode(cf.content).decode('utf-8')


class RepositoryInfo:

    def __init__(self, url: str, scan_tools: bool):
        self.url = url
        self.scan_tools = scan_tools

    def get_repository(self, g: Github):
        assert self.url.lower().startswith(GITHUB_URL.lower()), f'Invalid URL: {self.url}'
        url = self.url[len(GITHUB_URL):]
        url_match = re.match(GITHUB_REPOSITORY_PATTERN, url)
        assert url_match is not None, f'Invalid URL pattern: {self.url}'
        owner, name = url_match.group(1), url_match.group(2)
        try:
            return g.get_repo(f'{owner}/{name}')
        except UnknownObjectException:
            if name.endswith('.git'):
                return g.get_repo(f'{owner}/{name[:-4]}')
            else:
                raise


def get_github_repositories(g: Github) -> List[str]:
    """
    Get list of tool GitHub repositories to parse

    :param g: GitHub instance
    """
    with open('repositories.yml') as fp:
        data = yaml.safe_load(fp)
    repo_list: List[str] = list()
    for repo_spec in data['repositories']:
        kwargs = dict(scan_tools = repo_spec.get('scan-tools', True))
        if 'url-list' in repo_spec:
            for repo_line in urllib.request.urlopen(repo_spec['url-list']):
                repo_line = repo_line.decode('utf-8').split('#')[0].strip()
                if len(repo_line) > 0:
                    repo_info = RepositoryInfo(repo_line, **kwargs)
                    if repo_info.url.lower().startswith(GITHUB_URL.lower()):
                        repo_list.append(repo_info)
                    else:
                        warnings.warn(f'Not a GitHub URL, ignored: {repo_info.url}', stacklevel=2)
        elif 'url' in repo_spec:
            repo_list.append(RepositoryInfo(repo_url, **kwargs))
        elif 'owner-name' in repo_spec:
            repo_list.append(RepositoryInfo(GITHUB_URL + repo_spec['owner-name'], **kwargs))
    return repo_list


def is_subpath(subpath: Union[pathlib.Path, str], path: pathlib.Path) -> bool:
    return str(subpath) in [str(path)] + [str(p) for p in path.parents[:-1]]


def get_tool_directories(repository: Repository, commit: Commit, status: Optional[tqdm]=None) -> FrozenSet[str]:
    if status is not None: status.set_description_str('Fetching tree')
    try:
        tree = repository.get_git_tree(sha=commit.sha, recursive=True)
        return frozenset([str(pathlib.Path(te.path).parents[0]) for te in tree.tree if te.path.endswith('/' + SHED_FILENAME)])
    except UnknownObjectException:
        return frozenset()


def get_updated_tools(repository: Repository, commit: Commit, tool_directories: FrozenSet[str], status: Optional[tqdm]=None) -> List[dict]:
    """
    Get list of the tools for which tools have been added, updated, or removed.
    """
    updated_tools: List[str] = list()
    read_shed_files: Set[str] = set()

    for file in commit.files:
        for directory in pathlib.Path(file.filename).parents[:-1]:
            if str(directory) in tool_directories:
                shed_filepath = str(directory / SHED_FILENAME)
                if status is not None: status.set_description_str(f'Peeking {shed_filepath}')
                shed_file = get_string_content(repository.get_contents(shed_filepath, ref=commit.sha))

                # Make sure each tool (shed file) is processed only once
                if shed_file in read_shed_files: continue
                read_shed_files.add(shed_file)

                # Read the updated tool categories and add to set
                try:
                    shed_data = yaml.safe_load(shed_file)
                    assert shed_data is not None
                    categories = shed_data.get('categories')
                    assert categories is not None and all(map(lambda item: isinstance(item, str), categories))

                    # Record the tool if reading the categories was successful, i.e. the shed file is valid
                    tool = dict(name = directory.name, categories = list(sorted(categories)))
                    updated_tools.append(tool)

                # Do nothing if the file is not valid YAML or otherwise malformed
                except (yaml.YAMLError, AssertionError):
                    pass

                # We are done with this file, since a shed file was found
                break

    return list(sorted(updated_tools, key=lambda tool: tool['name']))


class process_new_commits:
    """
    Generator which yields all new commits in a repository.

    Each new commit is yielded along with its short SHA and datetime.
    Optionally, only new commits until a specified datetime are considered.
    New commits are determined by comparing each commit to the stock of previously known commits.
    The comparison is performed using the short SHA along with the datetime of the commits.
    The stock of previously known commits is represented by a pandas dataframe, and is expected to contain at least the columns `sha` and `timestamp`, where the values in the `timestamp` column correspond to the `str` representation of the datetime of each commit.
    """

    def __init__(self, repository: Repository, previous_commits: pd.DataFrame, until: Optional[datetime]=None):
        self.repository = repository
        self.previous_commits = previous_commits
        self.until = until
        self.status = None

    def __iter__(self):
        previous_commits_list = self.previous_commits[['sha', 'timestamp']].apply(tuple, axis=1).tolist()
        previous_commits_set = frozenset(previous_commits_list)
        try:
            assert len(self.previous_commits) == len(previous_commits_set), f'{len(self.previous_commits)} != {len(previous_commits_set)}'
        except AssertionError:
            print('\nConflicting commits:')
            for c, hc in dict(collections.Counter(previous_commits_list)).items():
                if hc > 1:
                    print(f'- {c[0]} {c[1]}')
            print('')
            raise
        
        get_commits_kwargs = dict(until=self.until) if self.until is not None else dict()
        commits = self.repository.get_commits(**get_commits_kwargs)
        new_commits_count = commits.totalCount - len(previous_commits_set)
        new_commits_processed = 0

        try:
            pbar = tqdm(total=new_commits_count, position=0)
            self.status = tqdm(total=0, bar_format='{desc}', position=1)

            for c in commits:
                if new_commits_processed >= new_commits_count: break

                short_sha = c.sha[:7]
                pbar.set_postfix_str(short_sha)
                datetime = pd.to_datetime(c.commit.author.date, utc=True)
                self.status.set_description_str(f'Current position: {datetime.strftime("%Y/%m/%d")}')

                if (short_sha, str(datetime)) in previous_commits_set: continue
                new_commits_processed += 1
                pbar.update(1)

                yield c, short_sha, datetime

        finally:
            pbar.close()
            self.status.close()
            self.status = None


def get_commit_author(commit: Commit) -> Optional[str]:
    if commit.author is None:
        return None
    else:
        try:
            return commit.author.login
        except IncompletableObject:
            return None


def get_commit_history(g: Github, rinfo: RepositoryInfo, until: Optional[datetime]=None) -> pd.DataFrame:
    repository = rinfo.get_repository(g)
    cached_df = cache.get_cached_commit_history(repository)
    new_entries = {c: list() for c in cached_df.columns}

    # Currently known tool directories, initially unknown
    tool_directories: FrozenSet[str] = None

    # Number of commits back in time, since shed files were last modified
    shed_age: int = 0

    for commit, short_sha, datetime in (pnc := process_new_commits(repository, cached_df, until)):

        # If a shed file is modified, then the tool directories become unknown without further inspection
        if any([file.filename.endswith('/' + SHED_FILENAME) for file in commit.files]):
            tool_directories = None
            shed_age = 0

        else:

            # Keep track of the number of commits back in time, since shed files were last modified
            # Example: 1 means that `c` is the first commit since the last modification
            shed_age += 1

        author: Optional[str] = get_commit_author(commit)
        if author is None:

            new_entries['author'].append('')
            new_entries['tools'].append('')

        else:

            # If enabled, fetch the directory tree and get list of updated tools
            updated_tool: List[dict]
            if rinfo.scan_tools:
                tool_directories: FrozenSet[str]  = get_tool_directories(repository, commit, pnc.status)
                updated_tools = get_updated_tools(repository, commit, tool_directories, pnc.status)
            else:
                updated_tools = list()

            new_entries['author'].append(author)
            new_entries['tools'].append(json.dumps(updated_tools))

        new_entries['timestamp'].append(str(datetime))
        new_entries['sha'].append(short_sha)

    pk = ['timestamp', 'sha']
    new_entries_df = pd.DataFrame(new_entries).iloc[::-1].drop_duplicates(pk)
    history_df = pd.concat([cached_df, new_entries_df]) if len(cached_df) > 0 else new_entries_df
    history_df.sort_values(pk, inplace=True)
    cache.set_cached_commit_history(repository, history_df)
    return history_df


def get_avatars(g: Github, column: str, cache_df: pd.DataFrame, get_avatar_url: Callable[[str], str], cache_column: Optional[str]=None) -> pd.DataFrame:
    if cache_column is None: cache_column = column

    repositories = cache.get_cached_repositories()
    values: Set[str] = set()
    for repo in repositories:
        df = pd.read_csv(f'cache/repositories/{repo}.csv')
        df['repository'] = repo
        df[column] = df[column].fillna('')
        values |= frozenset([value.lower() for value in df[column].values.tolist() if len(value) > 0])

    cache_data = {item[0]: item[1].tolist() for item in cache_df.to_dict('series').items()}

    now = datetime.now(timezone.utc)
    for value in tqdm(values, desc=f'Fetching "{column}" avatars'):
        sel = (cache_df[cache_column] == value)
        if sel.any():
            cache_row = cache_df[sel]
            if len(cache_row['avatar_url'].tolist()[0]) == 0: continue
            timestamp = pd.to_datetime(cache_row['timestamp'].tolist()[0], utc=True)
            if timestamp > now: continue

        try:
            avatar_url = get_avatar_url(value)
            cache_data['avatar_url'].append(avatar_url)
        except UnknownObjectException:
            cache_data['avatar_url'].append('')

        cache_data[cache_column].append(value)
        cache_data['timestamp'].append(now + timedelta(days=7 + random.randint(0, 23)))

    cache_df = pd.DataFrame(cache_data)
    cache_df.drop_duplicates(subset=[cache_column], keep='last', inplace=True)
    cache_df.sort_values(cache_column, inplace=True)
    return cache_df


def get_all_avatars(g: Github) -> pd.DataFrame:
    cache_df = cache.get_cached_avatars()
    cache_df = get_avatars(g, 'author', cache_df, lambda author: g.get_user(author).avatar_url, 'name')
    cache_df = get_avatars(g, 'repository', cache_df, lambda repository: g.get_repo(repository).owner.avatar_url, 'name')
    cache.set_cached_avatars(cache_df)
