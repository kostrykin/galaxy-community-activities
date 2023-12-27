from . import (
    cache,
    communitygraph,
    contributiongraph,
)

import os
import csv
import json
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


def expand_list(elist):
    items = list()
    for info in elist:
        if 'expand' in info:
            for item in urllib.request.urlopen(info['expand']):
                item = item.decode('utf-8').strip()
                items.append(item)
        else:
            assert isinstance(info, str), str(info)
            items.append(info)
    return items


def get_community_dataframe(community):

    # Get list of repositories relevant to the community
    if 'repositories' in community:
        repositories = community['repositories']
    else:
        repositories = cache.get_cached_repositories()

    # Get list of tool categories relevant to the community (if any)
    if 'categories' in community:
        categories = expand_list(community['categories'])
    else:
        categories = None

    # Get list of tools to keep even if it was ruled out due to the categories
    if 'keep-tools' in community:
        keep_tools = frozenset(expand_list(community['keep-tools']))
    else:
        keep_tools = frozenset()

    # Get list of tools to exclude even if categories match
    if 'exclude-tools' in community:
        exclude_tools = frozenset(expand_list(community['exclude-tools']))
    else:
        exclude_tools = frozenset()

    # Read the repositories and keep only the rows with matching categories
    df_list = list()
    for repo in repositories:
        df = pd.read_csv(cache.get_cached_repository_filepath(repo))
        if categories is not None or len(keep_tools) > 0:
            df.tools = df.tools.fillna('[]')

            # List of commits (row indices) to drop from the current dataframe
            drop_idx_list = list()

            for row_idx, row in enumerate(df.tools):
                row_tools = json.loads(row)

                # Names of tools from this community, affected by the current commit
                community_tools = set()

                # Iterate all tools affected by the current commit…
                for tool in row_tools:
                    keep = True

                    # …and filter by categories:
                    if categories is not None:
                        tool_categories = frozenset([c.lower().strip() for c in tool['categories']])
                        if not any([c.lower() in tool_categories for c in categories]):
                            keep = False

                    # …but also apply the rules from tool lists:
                    if tool['name'] in keep_tools:
                        keep = True

                    if tool['name'] in exclude_tools:
                        keep = False

                    if keep:
                        community_tools.add(tool['name'])

                # Drop this commit if it didn't concern any tools from this community
                if len(community_tools) == 0:
                    drop_idx_list.append(row_idx)

                # Otherwise, keep it and also record the names of the concerned tools
                else:
                    df.tools.iloc[row_idx] = ",".join(list(sorted(community_tools)))

            # Drop the commits listed for removal
            df.drop(drop_idx_list, inplace=True)

        else:
            df.tools = ''

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

        # Create dataframe for the tools of the community
        df_tools_rows = list()
        for _, row in df.iterrows():
            for tool in row.tools.split(','):
                tool = tool.strip()
                if len(tool) > 0:
                    df_tools_rows.append(dict(repository=row.repository, tool=tool))
        if len(df_tools_rows) > 0:
            df_tools = pd.DataFrame(df_tools_rows)
            df_tools.drop_duplicates(inplace=True)
            df_tools.sort_values(['repository', 'tool'], inplace=True)
            df_tools.to_csv(f'{communities_data_dir}/{cid}-tools.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)


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
