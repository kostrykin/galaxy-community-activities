# galaxy-community-activities
Tool which reports and summarizes activities within a Galaxy community.

Steps to setup locally:
- `mamba env create -f environment.yml`
- `source activate galaxy-community-activities`
- `ln -s $(which ruby) $CONDA_PREFIX/share/rubygems/bin/`
- `gem install jekyll`
