import os
import re
import glob
import csv
import urllib.request

import pandas as pd
import yaml
from liquid import Template


def get_community_dataframe(community):

    # Get list of repositories relevant to the community
    if 'repositories' in community:
        repositories = community['repositories']
    else:
        repositories = list()
        for cache_filepath in glob.glob('cache/*/*.csv'):
            match = re.match(r'^cache/(.*).csv$', cache_filepath)
            repositories.append(match.group(1))

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
        df = pd.read_csv(f'cache/{repo}.csv')
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

    # Render community pages
    os.makedirs('report/communities', exist_ok=True)
    for community in communities:
        df = get_community_dataframe(community)
        communities_data_dir = 'report/_data/communities_data'
        os.makedirs(communities_data_dir, exist_ok=True)
        df.to_csv(f'{communities_data_dir}/{community["id"]}.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)
        with open(f'report/communities/{community["id"]}.md', 'w') as fp:
            fp.write(template.render(community = community))


def update():
    update_communities()


def build():
    os.system('cd report && jekyll build')
