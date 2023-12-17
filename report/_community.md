---
title: {{ community.name }}
layout: default
community_id: {{ community.id }}
---

{% raw %}


<nav aria-label="breadcrumb">
  <ol class="breadcrumb">
    <li class="breadcrumb-item"><a href="../index.html">Home</a></li>
    <li class="breadcrumb-item active" aria-current="page">{{ page.title }}</li>
  </ol>
</nav>

<h1 class="mb-5">{{ page.title }}</h1>

{% assign community_data = site.data.communities_data[page.community_id] %}

<h2>Community Overview</h2>

**Commits:** {{ community_data.size }}

{% endraw %}
