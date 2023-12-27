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
javascript: |
  $("[data-toggle=popover]").popover({html: true})
  $("#communitygraph-link").on("click", function() {
    $('#communitygraph-full').attr('src', $('#communitygraph-thumbnail').attr('src'));
    $('#communitygraph-modal').modal('show');
    return false;
  });
  $("#repositorychart-link").on("click", function() {
    $('#repositorychart-full').attr('src', $('#repositorychart-thumbnail').attr('src'));
    $('#repositorychart-modal').modal('show');
    return false;
  });
---

{% raw %}

{% assign commits = site.data.communities_data[page.community_id] %}

<h2><small>Commits all-time: <b>{{ commits.size }}</b></small></h2>

{% assign contributors = commits | group_by: "author" | map: "name" | uniq %}
<p class="text-muted">from <b>{{ contributors.size }} contributors</b></p>

<h3><small><b>Most frequent contributors:</b></small></h3>
{% assign groups = commits | group_by: "author" | sort: "size" | reverse %}
{% assign groups = groups | where_exp: "g", "g.name.size > 0" %}
{% for g in groups limit: 6 %}
  {% include usercard.html name = g.name commits = g.items %}
{% endfor %}

{% if groups.size > 6 %}
<p>
And also:
{% for g in groups offset: 6 %}
  <a href="../contributors/{{ g.name }}.html">{{ g.name }}</a>{% if forloop.last == false %},{% endif %}
{% endfor %}
</p>
{% endif %}

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

{% if groups.size > 6 %}
<p>
And also:
{% for g in groups offset: 6 %}
  <a href="../contributors/{{ g.name }}.html">{{ g.name }}</a>{% if forloop.last == false %},{% endif %}
{% endfor %}
</p>
{% endif %}

<h3><small><b>New contributors:</b></small></h3>
{% assign groups = commits | group_by: "author" | sort: "size" | reverse %}
{% for g in groups %}
  {% assign commits_before_last_year = g.items | where_exp: "commit", "commit.timestamp < since_date" %}
  {% if commits_before_last_year.size == 0 %}
    {% include usercard.html name = g.name commits = g.items %}
  {% endif %}
{% endfor %}

<div>
{% assign communitygraph_path = "/assets/images/communitygraphs/" | append: page.community_id | append: ".png" %}
{% assign communitygraphs = site.static_files | where: "path", communitygraph_path %}
{% if communitygraphs.size > 0 %}
  <div class="community-float">
    <h3><small><b>Community graph:</b></small></h3>
    {% assign communitygraph = ".." | append: communitygraphs[0].path %}
    <a href="{{ communitygraph }}" id="communitygraph-link">
      <img id="communitygraph-thumbnail" src="{{ communitygraph }}" class="img-communitygraph img-thumbnail">
    </a>

    <!-- Creates the bootstrap modal where the image will appear -->
    <div class="modal fade" id="communitygraph-modal" tabindex="-1" role="dialog" aria-hidden="true">
      <div class="modal-dialog" style="max-width: 90%; width: auto;">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
            <h4 class="modal-title">Community graph</h4>
          </div>
          <div class="modal-body">
            <img src="" id="communitygraph-full" style="max-width: 100%; max-height: 100%;">
          </div>
        </div>
      </div>
    </div>
  </div>
{% endif %}
{% assign repositoryschart_path = "/assets/images/repositorycharts/" | append: page.community_id | append: ".svg" %}
{% assign repositoryscharts = site.static_files | where: "path", repositoryschart_path %}
{% if repositoryscharts.size > 0 %}
  <div class="community-float">
    <h3><small><b>Distribution of repositories:</b></small></h3>
    {% assign repositorychart = ".." | append: repositoryscharts[0].path %}
    <a href="{{ repositorychart }}" id="repositorychart-link">
      <img id="repositorychart-thumbnail" src="{{ repositorychart }}" class="img-repositorychart img-thumbnail">
    </a>

    <!-- Creates the bootstrap modal where the image will appear -->
    <div class="modal fade" id="repositorychart-modal" tabindex="-1" role="dialog" aria-hidden="true">
      <div class="modal-dialog" style="max-width: 90%; width: auto;">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
            <h4 class="modal-title">Distribution of repositories</h4>
          </div>
          <div class="modal-body">
            <img src="" id="repositorychart-full" style="max-width: 100%; max-height: 100%;">
          </div>
        </div>
      </div>
    </div>
  </div>
{% endif %}
</div>

{% assign dataname = page.community_id | append: "-tools" %}
{% assign tools = site.data.communities_data[dataname] %}
{% if tools %}
---
<h2><small>Repositories: <b>{{ tools.size }} tools</b></small></h2>
{% assign repositories = tools | group_by: "repository" %}
{% if repositories %}
{% assign repositories = repositories | sort: "size" | reverse %}
{% for repo in repositories %}
{% assign repo_id = repo.name | slugify %}
<p>
  <button class="btn btn-link" type="button" data-toggle="collapse" data-target="#{{ repo_id }}" aria-expanded="false" aria-controls="{{ repo_id }}">
    {{ repo.name }}
  </button>
  ({{ repo.items.size }})
  <div class="collapse" id="{{ repo_id }}">
    <div class="card card-body">
      <ol>
        {% for item in repo.items %}
          <li>{{ item.tool }}</li>
        {% endfor %}
      </ol>
    </div>
  </div>
</p>
{% endfor %}
{% endif %}
{% endif %}

{% endraw %}
