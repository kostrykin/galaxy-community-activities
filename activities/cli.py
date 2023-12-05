import argparse
import os
from . import fetch


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--api', help='GitHub access token', default=None)
    args = parser.parse_args()

    if args.api is None:
        args.api = os.environ.get('GITHUB_TOKEN')

    g = fetch.Github(args.api)
    repositories = fetch.get_tool_github_repositories(g)
    
    for repository_url in repositories:
        if 'bmcv' not in repository_url.lower(): continue
        repo = fetch.get_github_repository(g, repository_url)
        #for c in repo.get_commits():
        #    if c.author is None: continue
        #    print(c.author.login, c.last_modified)
        #    file = c.files[0]
        #    print(file.contents_url, file.blob_url)
        #    print('---')
        #    print(fetch.get_string_content(repo.get_contents(file.filename, ref=c.sha)))
        #    break
        #break
        fetch.get_commit_history(repo)