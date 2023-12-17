---
title: {{ community.name }}
layout: default
community_id: {{ community.id }}
breadcrumb:
  - '<a href="../index.html">Home</a>'
  - '{{ community.name }}'
---

{% raw %}

{% assign community_data = site.data.communities_data[page.community_id] %}

**Commits:** {{ community_data.size }}

**Most frequent contributors:**
{% assign groups = community_data | group_by: "author" | sort: "size" | reverse %}
<ol>
  {% for g in groups limit: 5 %}
  <li>{{ g.name }} {{ g.items.size }}</li>
  {% endfor %}
</ol>

{% endraw %}
