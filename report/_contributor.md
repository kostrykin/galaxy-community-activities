---
title: {{ contributor }}
intro: |
  <p>
    <i class="bi bi-box-arrow-up-right"></i>
    <a href="https://github.com/{{ contributor }}">https://github.com/{{ contributor }}</a>
  </p>
layout: default
contributor: {{ contributor }}
breadcrumb:
  - '<a href="../index.html">Galaxy Community Activities</a>'
  - '{{ contributor }}'
---

{% raw %}

{% assign username = page.contributor | downcase %}
{% assign avatars = site.data.avatars | where_exp: "author", "author.name == username" %}
{% assign avatar = avatars[0] %}

<div class="container">
<div class="row">
  <div class="col-lg-3"><img src="{{ avatar.avatar_url }}" class="img-circle" style="width: 100%;"></div>
  <div class="col-lg-9">

{% assign commits = site.data.contributors_data[page.contributor] %}

<h2><small>Commits all-time: <b>{{ commits.size }}</b></small></h2>

{% assign since_year = site.time | date: '%Y' | minus:1 %}
{% assign since_month_day = site.time | date: '%m-%d' %}
{% assign since_date = since_year | append: "-" | append: since_month_day %}
{% assign commits_last_year = commits | where_exp: "commit", "commit.timestamp >= since_date" %}
<h2><small>Commits last year: <b>{{ commits_last_year.size }}</b></small></h2>

{% assign contributiongraph_path = "/assets/images/contributiongraphs/" | append: page.contributor | append: ".png" %}
{% assign contributiongraphs = site.static_files | where: "path", contributiongraph_path %}
{% if contributiongraphs.size > 0 %}
  {% assign contributiongraph = ".." | append: contributiongraphs[0].path %}
  <img src="{{ contributiongraph }}" class="img-contributiongraph">
{% endif %}

  </div>
</div>
</div>

{% endraw %}