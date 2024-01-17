# [galaxy-community-activities]()

[![Update cache](https://github.com/kostrykin/galaxy-community-activities/actions/workflows/update_cache.yml/badge.svg)](https://github.com/kostrykin/galaxy-community-activities/actions/workflows/update_cache.yml)
[![Build and deploy](https://github.com/kostrykin/galaxy-community-activities/actions/workflows/build_and_deploy.yml/badge.svg)](https://github.com/kostrykin/galaxy-community-activities/actions/workflows/build_and_deploy.yml)

Tool which reports and summarizes activities within a Galaxy community.

For more info, see the [announcement on galaxyproject.org](https://galaxyproject.org/news/2024-01-galaxy-community-activities/).

Updates are scheduled weekly.

## Local setup

Steps to setup locally:
- `mamba env create -f environment.yml`
- `source activate galaxy-community-activities`
- `gem install jekyll`
- `ln -s $(which ruby) $CONDA_PREFIX/share/rubygems/bin/`

## Update the cache

Set your GitHub PAT as `GITHUB_TOKEN` or use `--api` to pass it via command line: 
```bash
python -m activities.cli --fetch
```

## Build the report from cache

```bash
python -m activities.cli --report
```
