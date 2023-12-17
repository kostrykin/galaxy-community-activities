import os

import pandas as pd
import yaml
from liquid import Template


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
        with open(f'report/communities/{community["id"]}.md', 'w') as fp:
            fp.write(template.render(community = community))


def update():
    update_communities()


def build():
    os.system('cd report && jekyll build')
