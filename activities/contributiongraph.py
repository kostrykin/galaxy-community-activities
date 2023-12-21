from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Optional,
)
import os, os.path
import warnings
import tempfile

import numpy as np
import pandas as pd
import pygraphviz as pgv
from liquid import Template

from .graphs import (
    AvatarCache,
    node_label_prefix,
    node_kwargs,
    filter_by_timestamp,
)


def days_between(first, last, df, step=1):
    assert step >= 1, step

    if first is None:
        first = pd.to_datetime(df['timestamp']).min()
    if last is None:
        last = pd.to_datetime(df['timestamp']).max()

    day = first.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= last:
        yield day
        day = day + timedelta(days=step)


def create_timeline_dot(nodes):
    dot_template = Template(
        """
        digraph G {
            subgraph cluster_timeline {
                peripheries=0
                { graph[rank=same]; {{ node_names | join: ", " }}; }
                {{ node_names | join: "->" }} [style=invis]
                {% for node in node_names %}
                {{ node }} [
                    {% for property in properties[node] %}
                    {{ property[0] }}="{{ property[1] }}"
                    {% endfor %}
                ]
                {% endfor %}
            }
        }
        """)
    return dot_template.render(
        node_names = [node[0] for node in nodes],
        properties = {node[0]: node[1] for node in nodes})


def get_unique_colors(n, sat=0.6, val=0.9):
    return [f'{hue:f} {sat:f} {val:f}' for hue in np.linspace(0, 1, num=n, endpoint=False)]


def render_contribution_graph(filepath: str, contributor: str, since: Optional[datetime]=None, until: Optional[datetime]=None):
    df_contributions = pd.read_csv(f'report/_data/contributors_data/{contributor}.csv')
    df_contributions.repository = df_contributions.repository.fillna('')
    df_contributions = filter_by_timestamp(df_contributions, first_day=since, last_day=until)

    # Delete previous contributiongraph and drop out, if there were no contributions in the given timeframe
    if len(df_contributions) == 0:
        if os.path.isfile(filepath):
            os.remove(filepath)
        return

    # Get involed repositories
    repositories = np.unique([repository for repository in df_contributions['repository'].tolist() if len(repository) > 0])
    repo_colors = dict(zip(repositories, get_unique_colors(len(repositories))))

    # Get required avatars
    avatar_cache = AvatarCache()
    avatar_cache.load([], repositories)

    # Compute timeline nodes and repository edges
    previous_day = None
    timeline_nodes = list()
    edges = list()
    contributions_datetime = pd.to_datetime(df_contributions.timestamp, utc=True)
    for day_idx, day in enumerate(days_between(since, until, df_contributions, step=7)):
        node_id = f'day{day_idx}'
        label = (day.strftime('%-d. %b %y') + '\n ') if previous_day is not None and day.month != previous_day.month else ' '
        timeline_nodes.append((
            node_id,
            dict(
                label=label,
                shape='circle',
                style='filled',
                color='0 0 0.3' if len(label.strip()) > 0 else 'white',
                fontcolor='0 0 0.3',
                fixedsize='true',
                width=0.33,
                height=0.33)))
        if previous_day is not None:
            contributions_mask = np.logical_and(
                contributions_datetime >= (previous_day + timedelta(days=1)),
                contributions_datetime < (day + timedelta(days=1)),
            )
            df_contributions_today = df_contributions[contributions_mask]
            for repo in np.unique([repository for repository in df_contributions_today.repository.tolist() if len(repository) > 0]):
                edges.append((node_id, repo))
        previous_day = day

    # Create base graph
    G_dot = create_timeline_dot(timeline_nodes)
    with tempfile.NamedTemporaryFile(mode='w') as fp:
        fp.write(G_dot)
        try:
            G = pgv.AGraph(fp.name)
        except pgv.agraph.DotError:
            G_dot_filename = f'.failed-G.{contributor}.dot'
            with open(G_dot_filename, 'w') as fp:
                fp.write(G_dot)
            print(f'*** dot file written to: {G_dot_filename}')
            raise

    # Add graph nodes (repositories)
    for repo in repositories:
        label_parts = repo.split('/')
        label = f'{node_label_prefix}{label_parts[0]}/\n{label_parts[1]}'
        G.add_node(repo, image=avatar_cache.get_filename(repo), type='repository', label=label, **node_kwargs)

    # Add graph edges (timeline to repositories)
    for node_id, repo in edges:
        G.add_edge(
            node_id,
            repo,
            color=repo_colors[repo],
            headclip='false',
            tailclip='false')

    # Update graph style
    G.graph_attr.update(remincross='false')
    G.graph_attr.update(bgcolor='0 0 0.937')
    G.graph_attr.update(outputorder='edgesfirst')
    G.graph_attr.update(pad='0.2,0.8')
    G.node_attr.update(fontname='Helvetica')
    G.node_attr.update(fontsize='28')
    G.node_attr.update(labelloc='b')
    G.node_attr.update(penwidth=0)
    G.edge_attr.update(penwidth=2)
    G.edge_attr.update(splines='curved')

    # Do the layout and draw the graph
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fmt = filepath.split('.')[-1].lower()

        G.layout(prog='dot')
        G.draw(path=filepath, format=fmt)
