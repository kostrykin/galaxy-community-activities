from datetime import (
    datetime,
)
from typing import (
    Optional,
)

import numpy as np
import pandas as pd
import networkx as nx

from .graphs import AvatarCache


node_label_prefix = '\n\n\n\n\n'
node_kwargs = dict(shape='box')


def remove_edges_from(G, n):
    for u, v in G.edges:
        if u == n or v == n:
            G.remove_edge(u, v)


def simplify_graph(G: nx.Graph, authors, repositories, avatar_cache, max_edges=50, max_nodes=np.inf):
    while True:
        
        # Break when the graph is sufficiently simple
        if len(G.edges) <= max_edges and len(G.nodes) <= max_nodes: break

        # Choose the node with the highest degree
        n, n_deg = max(G.degree, key=lambda n: n[1])
        if n_deg == 2:
            break ## Nothing left to simplify here

        # Create proxy node
        remove_edges_from(G, n)
        if '/' in n:
            proxy = f'{node_label_prefix}{n_deg:d} contributors\n({100 * n_deg / len(authors):.0f}%)'
            proxy_type = 'author'
        else:
            proxy = f'{node_label_prefix}{n_deg:d} repositories\n({100 * n_deg / len(repositories):.0f}%)'
            proxy_type = 'repository'
        G.add_node(proxy, type=proxy_type, image=avatar_cache.get_filename('.blank'), **node_kwargs)
        G.add_edge(proxy, n, headclip='false', tailclip='false')

        # Remove disconnected nodes
        disconnected_nodes = list()
        for n in G.nodes:
            if G.degree[n] == 0:
                disconnected_nodes.append(n)
        for n in disconnected_nodes:
            G.remove_node(n)


def render_community_graph(filepath: str, community_id: str, community_name: str, cache_dir: str='cache/avatars', since: Optional[datetime]=None, until: Optional[datetime]=None, spread: float=1, seed: int=1):
    assert spread > 0, spread

    df_community = pd.read_csv(f'report/_data/communities_data/{community_id}.csv')
    if since is not None:
        df_community = df_community[df_community['timestamp'] >= since.strftime('%Y-%m-%d')]
    if until is not None:
        df_community = df_community[df_community['timestamp'] <= until.strftime('%Y-%m-%d')]

    # Get involed authors and repositories
    df_community.author = df_community.author.fillna('')
    df_community.repository = df_community.repository.fillna('')
    authors = np.unique([author for author in df_community['author'].tolist() if len(author) > 0])
    repositories = np.unique([repository for repository in df_community['repository'].tolist() if len(repository) > 0])

    # Get required avatars
    avatar_cache = AvatarCache(cache_dir)
    avatar_cache.load(authors, repositories)

    # Create graph
    G = nx.Graph()

    # Create graph nodes
    for repo in repositories:
        label_parts = repo.split('/')
        label = f'{node_label_prefix}{label_parts[0]}/\n{label_parts[1]}'
        G.add_node(repo, image=avatar_cache.get_filename(repo), type='repository', label=label, **node_kwargs)
    for author in authors:
        label = f'{node_label_prefix}{author}\n ' ## The tailing whitespace is mandatory
        G.add_node(author, image=avatar_cache.get_filename(author), type='author', label=label, **node_kwargs)

    # Create graph edges
    edges = df_community[['author', 'repository']].drop_duplicates()
    for _, edge in edges.iterrows():
        if len(edge['author']) == 0 or len(edge['repository']) == 0: continue
        G.add_edge(edge['author'], edge['repository'], headclip='false', tailclip='false')

    # Simplify graph
    simplify_graph(G, authors, repositories, avatar_cache)

    # Export graph to pygraphviz for drawing
    A = nx.nx_agraph.to_agraph(G)
    A.graph_attr.update(size='25,25')
    A.graph_attr.update(bgcolor='0 0 0.937')
    A.graph_attr.update(outputorder='edgesfirst')
    A.graph_attr.update(overlap='prism')
    A.graph_attr.update(overlap_scaling='-1')
    A.graph_attr.update(labelloc='t')
    A.graph_attr.update(labeljust='l')
    A.graph_attr.update(fontsize='42')
    A.graph_attr.update(fontname='Helvetica')
    A.node_attr.update(fontname='Helvetica')
    A.node_attr.update(fontsize='28')
    A.node_attr.update(labelloc='b')
    A.node_attr.update(penwidth=0)
    A.edge_attr.update(penwidth=10)
    A.edge_attr.update(color='0 0 1')
    A.layout(prog='neato')

    datetime_fmt = '%d.%m.%Y'
    since_str = pd.to_datetime(df_community.timestamp.min(), utc=True).strftime(datetime_fmt)
    until_str = pd.to_datetime(df_community.timestamp.max(), utc=True).strftime(datetime_fmt)
    A.graph_attr.update(label=f'{community_name} ({since_str}–{until_str})')

    # Draw the graph
    fmt = filepath.split('.')[-1].lower()
    A.draw(path=filepath, format=fmt)
