from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Optional,
)

import numpy as np
import pandas as pd
import networkx as nx

from .graphs import (
    AvatarCache,
    node_label_prefix,
    node_kwargs,
)


def days_between(first, last, df):
    if first is None:
        first = pd.to_datetime(df['timestamp']).min()
    if last is None:
        last = pd.to_datetime(df['timestamp']).max()

    day = first
    while day <= last:
        yield day
        day = day + timedelta(days=1)


def render_contribution_graph(filepath: str, contributor: str, since: Optional[datetime]=None, until: Optional[datetime]=None):
    df_contributions = pd.read_csv(f'report/_data/contributors_data/{contributor}.csv')
    df_contributions.repository = df_contributions.repository.fillna('')
    if since is not None:
        df_contributions = df_contributions[df_contributions['timestamp'] >= since.strftime('%Y-%m-%d')]
    if until is not None:
        df_contributions = df_contributions[df_contributions['timestamp'] <= until.strftime('%Y-%m-%d')]

    # Get involed repositories
    repositories = np.unique([repository for repository in df_contributions['repository'].tolist() if len(repository) > 0])

    # Get required avatars
    avatar_cache = AvatarCache()
    avatar_cache.load([], repositories)

    # Create graph
    G = nx.Graph()

    # Create graph nodes (days)
    for day in days_between(since, until, df_contributions):
        node_id = day.strftime('%Y-%m-%d')
        label = day.strftime('%d.%m.%Y') if day.day == 1 else ''
        G.add_node(node_id, type='day', label=label)

    # Create graph nodes (repositories)
    for repo in repositories:
        label_parts = repo.split('/')
        label = f'{node_label_prefix}{label_parts[0]}/\n{label_parts[1]}'
        G.add_node(repo, image=avatar_cache.get_filename(repo), type='repository', label=label, **node_kwargs)
