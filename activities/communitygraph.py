import math
from datetime import (
    datetime,
)
from typing import (
    Optional,
)

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import skimage, skimage.io
import scipy.ndimage as ndi
from PIL import Image, ImageDraw


def load_image_url(url):
    img = skimage.io.imread(url, plugin='matplotlib')
    return skimage.img_as_float(img)

def image_to_disk(img):
    mask = np.ones(img.shape[:2], bool)
    mask[mask.shape[0] // 2, mask.shape[1] // 2] = False
    mask = ndi.distance_transform_edt(mask) < min(mask.shape) // 2 - 2
    return np.concatenate([img[:, :, :3], mask[:, :, None]], axis=2)

def image_to_rounded_square(img):
    assert img.shape[2] in (3, 4), img.shape
    
    # Create mask of appropriate size (square with rounded corners)
    size = max(img.shape[:2])
    mask = Image.new('RGB', (size, size), 'black')
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), fill='white', width=0, radius=round(size * 0.2))
    mask = np.asarray(mask)[:, :, 0].copy()
    
    # Convert RGBA image to RGB with white background
    if img.shape[2] == 4:
        img_RGB = img[:, :, :3]
        img_A = img[:, :, 3][:, :, None]
        img = (1 + (img_RGB - 1) * img_A)
    
    # Convert to RGBA using the alpha channel from the mask
    result = np.concatenate([img, mask[:, :, None]], axis=2)
    return result.clip(0, 1)


def remove_edges_from(G, n):
    for u, v in G.edges:
        if u == n or v == n:
            G.remove_edge(u, v)


def simplify_graph(G: nx.Graph, authors, repositories, max_edges=50, max_nodes=30):
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
            proxy = f'{100 * n_deg / len(authors):.0f}% of\ncontributors'
            proxy = f'{n_deg:d} contributors'
            proxy_type = 'author'
        else:
            proxy = f'{100 * n_deg / len(repositories):.0f}% of\nrepositories'
            proxy = f'{n_deg:d} repositories'
            proxy_type = 'repository'
        G.add_node(proxy, image=None, type=proxy_type)
        G.add_edge(proxy, n)

        # Remove disconnected nodes
        disconnected_nodes = list()
        for n in G.nodes:
            if G.degree[n] == 0:
                disconnected_nodes.append(n)
        for n in disconnected_nodes:
            G.remove_node(n)


def render_community_graph(filepath: str, community_id: str, since: Optional[datetime]=None, until: Optional[datetime]=None, spread: float=1, seed: int=1):
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
    df_avatars = pd.read_csv('report/_data/avatars.csv')
    df_avatars.set_index('name', inplace=True)
    avatars = dict()
    for username in authors:
        avatars[username] = image_to_disk(load_image_url(df_avatars.loc[username.lower()].avatar_url))
    for reponame in repositories:
        avatars[reponame] = image_to_rounded_square(load_image_url(df_avatars.loc[reponame.lower()].avatar_url))

    # Create graph
    G = nx.Graph()

    # Create graph nodes
    for repo in repositories:
        G.add_node(repo, image=avatars[repo], type='repository')
    for author in authors:
        G.add_node(author, image=avatars[author], type='author')

    # Create graph edges
    edges = df_community[['author', 'repository']].drop_duplicates()
    for _, edge in edges.iterrows():
        if len(edge['author']) == 0 or len(edge['repository']) == 0: continue
        G.add_edge(edge['author'], edge['repository'])

    # Simplify graph
    simplify_graph(G, authors, repositories)

    # Get a reproducible layout and create figure
    pos = nx.spring_layout(G, seed=seed, k=spread, iterations=100)
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot()

    # Render the graph
    nx.draw(
        G,
        pos=pos,
        ax=ax,
        arrows=True,
        arrowstyle="-",
        arrowsize=50,
        edge_color='#fff',
        width=5,
    )

    # Define offset of label positions (wrt node position)
    def get_label_positions(pos):
        return {node: p + (0, -0.09) for node, p in pos.items()}

    # Render labels
    for mode in ('repository', 'author'):
        nx.draw_networkx_labels(
            G,
            pos=get_label_positions(pos),
            font_size=14,
            font_weight='bold' if mode == 'repository' else 'normal',
            labels={n: n.replace('/', '/\n') for n in G.nodes if G.nodes[n]['type'] == mode}
        )

    # Update figure
    fig.set_facecolor('0.937')
    
    # Transform from data coordinates (scaled between xlim and ylim) to display coordinates
    tr_figure = ax.transData.transform

    # Transform from display to figure coordinates
    tr_axes = fig.transFigure.inverted().transform
    
    # Select the size of the image (relative to the X axis)
    icon_size = (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.025
    icon_center = icon_size / 2
    
    # Add the respective image to each node
    for n in G.nodes:
        if G.nodes[n]['image'] is None: continue
        xf, yf = tr_figure(pos[n])
        xa, ya = tr_axes((xf, yf))

        # Get overlapped axes and plot icon
        icon_size_factor = 0.7 if '/' in n else 1
        a = plt.axes([
            xa - icon_center * icon_size_factor,
            ya - icon_center * icon_size_factor,
            icon_size * icon_size_factor,
            icon_size * icon_size_factor])
        a.imshow(G.nodes[n]['image'])
        a.axis('off')

    # Save the figure
    fig.savefig(filepath, bbox_inches='tight')
    plt.close(fig)
