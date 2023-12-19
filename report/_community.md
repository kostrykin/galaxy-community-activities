---
title: {{ community.name }}
subtitle: {{ community.short_name }}
intro: |
  {% if community.url %}
    <p>
      <i class="bi bi-box-arrow-up-right"></i>
      <a href="https://{{ community.url }}">{{ community.url }}</a>
    </p>
  {% endif%}
layout: default
community_id: {{ community.id }}
breadcrumb:
  - '<a href="../index.html">Galaxy Community Activities</a>'
  - '{{ community.name }}'
---

{% raw %}

{% assign commits = site.data.communities_data[page.community_id] %}

<h2><small>Commits all-time: <b>{{ commits.size }}</b></small></h2>

<h3><small><b>Most frequent contributors:</b></small></h3>
{% assign groups = commits | group_by: "author" | sort: "size" | reverse %}
{% assign groups = groups | where_exp: "g", "g.name.size > 0" %}
{% for g in groups limit: 6 %}
  {% include usercard.html name = g.name commits = g.items %}
{% endfor %}

---

{% assign since_year = site.time | date: '%Y' | minus:1 %}
{% assign since_month_day = site.time | date: '%m-%d' %}
{% assign since_date = since_year | append: "-" | append: since_month_day %}
{% assign commits_last_year = commits | where_exp: "commit", "commit.timestamp >= since_date" %}
<h2><small>Commits last year: <b>{{ commits_last_year.size }}</b></small></h2>

<h3><small><b>Most frequent contributors:</b></small></h3>
{% assign groups = commits_last_year | group_by: "author" | sort: "size" | reverse %}
{% assign groups = groups | where_exp: "g", "g.name.size > 0" %}
{% for g in groups limit: 6 %}
  {% include usercard.html name = g.name commits = g.items %}
{% endfor %}

<h3><small><b>New contributors:</b></small></h3>
{% assign groups = commits | group_by: "author" | sort: "size" | reverse %}
{% for g in groups %}
  {% assign commits_before_last_year = g.items | where_exp: "commit", "commit.timestamp < since_date" %}
  {% if commits_before_last_year.size == 0 %}
    {% include usercard.html name = g.name commits = g.items %}
  {% endif %}
{% endfor %}

{% assign communitygraph_path = "/assets/images/communitygraphs/" | append: page.community_id | append: ".svg" %}
{% assign communitygraphs = site.static_files | where: "path", communitygraph_path %}
{% if communitygraphs.size > 0 %}
  <img src="..{{ communitygraphs[0].path }}" class="img-communitygraph">
{% endif %}

{% endraw %}
