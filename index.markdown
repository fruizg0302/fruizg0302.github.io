---
layout: default
---

# Blog Posts

{% for post in site.posts %}
## [{{ post.title }}]({{ post.url }})
*{{ post.date | date: "%B %d, %Y" }}*

{{ post.excerpt }}

[Read more →]({{ post.url }})

---
{% endfor %}
