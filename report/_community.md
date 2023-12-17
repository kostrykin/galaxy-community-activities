---
title: {{ community.name }}
layout: default
community_id: {{ community.id }}
breadcrumb:
  - '<a href="../index.html">Home</a>'
  - '{{ community.name }}'
---

{% raw %}

{% assign commits = site.data.communities_data[page.community_id] %}

**Commits all-time:** {{ commits.size }}

**Most frequent contributors:**
{% assign groups = commits | group_by: "author" | sort: "size" | reverse %}
<ol>
{% for g in groups limit: 5 %}
  <li>{% include usercard.html name = g.name commits = g.items.size %}</li>
{% endfor %}
</ol>

{% assign since_year = site.time | date: '%Y' | minus:1 %}
{% assign since_month_day = site.time | date: '%m-%d' %}
{% assign since_date = since_year | append: "-" | append: since_month_day %}
{% assign commits_last_year = commits | where_exp: "commit", "commit.timestamp >= since_date" %}
**Commits last year:**
{{ commits_last_year.size }}

**Most frequent contributors:**
{% assign groups = commits_last_year | group_by: "author" | sort: "size" | reverse %}
<ol>
{% for g in groups limit: 5 %}
  <li>{% include usercard.html name = g.name commits = g.items.size %}</li>
{% endfor %}
</ol>

**New contributors:**
{% assign groups = commits | group_by: "author" %}
<ol>
{% for g in groups %}
  {% assign commits_before_last_year = g.items | where_exp: "commit", "commit.timestamp < since_date" %}
  {% if commits_before_last_year.size == 0 %}
    {% assign repositories = g.items | map: "repository" | uniq %}
    <li>{% include usercard.html name = g.name repositories = repositories %}</li>
  {% endif %}
{% endfor %}
</ol>

{% endraw %}
