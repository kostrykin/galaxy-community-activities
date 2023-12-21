from . import (
    cache,
    communitygraph,
    contributiongraph,
)

import os
import csv
import urllib.request
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pandas as pd
import yaml
from liquid import Template
from tqdm import tqdm


def get_community_dataframe(community):

    # Get list of repositories relevant to the community
    if 'repositories' in community:
        repositories = community['repositories']
    else:
        repositories = cache.get_cached_repositories()

    # Get list of tool categories relevant to the community (if any)
    if 'categories' in community:
        categories = list()
        for cinfo in community['categories']:
            if 'expand' in cinfo:
                for category in urllib.request.urlopen(cinfo['expand']):
                    category = category.decode('utf-8').strip()
                    categories.append(category)
            else:
                assert isinstance(cinfo, str), str(cinfo)
                categories.append(cinfo)
                
    else:
        categories = None

    # Read the repositories and keep only the rows with matching categories
    df_list = list()
    for repo in repositories:
        df = pd.read_csv(cache.get_cached_repository_filepath(repo))
        df.categories = df.categories.fillna('')
        if categories is not None:
            drop_idx_list = list()
            for row_idx, row in enumerate(df['categories']):
                row_categories = [c.lower().strip() for c in row.split(',')]
                if not any([c.lower() in row_categories for c in categories]):
                    drop_idx_list.append(row_idx)
            df.drop(drop_idx_list, inplace=True)
        df['repository'] = repo
        df_list.append(df)
    return pd.concat(df_list)


def update_communities():

    # Load communities
    with open('communities.yml') as fp:
        communities = yaml.safe_load(fp)['communities']

    # Load template
    with open('report/_community.md') as fp:
        template = Template(fp.read())

    # Prepare directory for community graphs
    communitygraphs_dir = 'report/assets/images/communitygraphs'
    os.makedirs(communitygraphs_dir, exist_ok=True)

    # Render community pages
    os.makedirs('report/communities', exist_ok=True)
    for community in (pbar := tqdm(communities)):
        cid = community['id']
        pbar.set_description_str(cid)
        df = get_community_dataframe(community)
        communities_data_dir = 'report/_data/communities_data'
        os.makedirs(communities_data_dir, exist_ok=True)
        df.to_csv(f'{communities_data_dir}/{cid}.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)

        # Render community graph for the last year (if there is more than one repository)
        if len(df.repository.drop_duplicates()) > 1:
            since = datetime.now(timezone.utc) - timedelta(days=365)
            communitygraph.render_community_graph(f'{communitygraphs_dir}/{cid}.png', cid, community['name'], since=since)

        # Render the community template
        with open(f'report/communities/{cid}.md', 'w') as fp:
            fp.write(template.render(community = community))


def get_contributors():

    # Get cached contributors
    repositories = cache.get_cached_repositories()

    # Read cached repositories
    df_list = list()
    for repo in repositories:
        df = pd.read_csv(cache.get_cached_repository_filepath(repo))
        df['repository'] = repo
        df.author.fillna('')
        df_list.append(df)
    df = pd.concat(df_list)

    # Sort by contributors
    contributors = df.author.drop_duplicates().values
    return {contributor: df[df['author'] == contributor] for contributor in contributors}


def update_contributors():
    contributors_data_dir = 'report/_data/contributors_data'
    os.makedirs(contributors_data_dir, exist_ok=True)

    # Load template
    with open('report/_contributor.md') as fp:
        template = Template(fp.read())

    # Prepare directory for contribution graphs
    contributiongraphs_dir = 'report/assets/images/contributiongraphs'
    os.makedirs(contributiongraphs_dir, exist_ok=True)

    # Render contributor pages
    os.makedirs('report/contributors', exist_ok=True)
    for contributor, contributions in tqdm(get_contributors().items(), desc='Updating contributors'):
        contributions.to_csv(f'{contributors_data_dir}/{contributor}.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)

        # Render contribution graph for the last year
        since = datetime.now(timezone.utc) - timedelta(days=365)
        until = datetime.now(timezone.utc)
        contributiongraph.render_contribution_graph(f'{contributiongraphs_dir}/{contributor}.png', contributor, since=since, until=until)

        # Render the community template
        with open(f'report/contributors/{contributor}.md', 'w') as fp:
            fp.write(template.render(contributor = contributor))


def update():
    update_communities()
    update_contributors()


def build():
    os.system('cd report && jekyll build')
