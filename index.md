---
layout: default
title: Home
---

# AI Virtual Agent Blog

Technical articles about building cloud-native AI solutions with OpenShift AI, virtual agents, and enterprise integrations.

## Blog Posts

{% for post in site.posts %}
  <article>
    <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    <p class="post-meta">{{ post.date | date: "%B %-d, %Y" }}</p>
    {% if post.excerpt %}
      {{ post.excerpt }}
    {% endif %}
  </article>
{% endfor %}
