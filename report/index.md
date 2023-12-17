---
title: Galaxy Community Activities
layout: default
---

<h1 class="mb-5">{{ page.title }}</h1>

**Communities:**

<ul class="mb-5">
{% for community in site.data.communities.communities %}
<li><a href="communities/{{ community.id }}.html">{{ community.name }}</a></li>
{% else %}
<li>No communities.</li>
{% endfor %}
</ul>

---

<p class="text-muted"><small>
<b>Is your community missing?</b>
Add it on <a href="https://github.com/kostrykin/galaxy-community-activities"><i class="bi bi-github"></i> GitHub</a>.
</small></p>
