---
layout: default
title: Dodgers Dashboard
permalink: /
---

<div class="container">
    <h1 class="headline">{{ site.headline }}</h1>
    <p class="subhead">{{ site.data.season_summary_latest | where: "stat", "summary" | map: "value" | first }} </p>

<div class="container mt-4">
<h2 class="stat-group">Standings</h2>
  <div class="row">
    {% for item in site.data.season_summary_latest %}
      {% if item.category == 'standings' %}
      <div class="col-md-4">
        <div class="card mb-4">
          <div class="card-header">
            {{ item.stat_label }}
          </div>
          <div class="card-body">
            <p class="card-text">{{ item.value }}</p>
          </div>
          <div class="card-footer text-muted">
        {{ item.context_value_label }}: {{ item.context_value }}
          </div>
        </div>
      </div>
      {% endif %}
    {% endfor %}
  </div>
  <h2 class="stat-group">Standings: 2024 vs. past</h2>
<div id="d3-container" style="width: 100%; padding-bottom: 20px;">
</div>
<h2 class="stat-group">Batting</h2>
  <div class="row">
    {% for item in site.data.season_summary_latest %}
      {% if item.category == 'batting' %}
      <div class="col-md-4">
        <div class="card mb-4">
          <div class="card-header">
            {{ item.stat_label }}
          </div>
          <div class="card-body">
            <p class="card-text">{{ item.value }}</p>
          </div>
          <div class="card-footer text-muted">
        {{ item.context_value_label }}: {{ item.context_value }}
          </div>
        </div>
      </div>
      {% endif %}
    {% endfor %}
  </div>
  <h2 class="stat-group"> Pitching</h2>
  <div class="row">
    {% for item in site.data.season_summary_latest %}
      {% if item.category == 'pitching' %}
      <div class="col-md-4">
        <div class="card mb-4">
          <div class="card-header">
            {{ item.stat_label }}
          </div>
          <div class="card-body">
            <p class="card-text">{{ item.value }}</p>
          </div>
          <div class="card-footer text-muted">
        {{ item.context_value_label }}: {{ item.context_value }}
          </div>
        </div>
      </div>
      {% endif %}
    {% endfor %}
  </div>
</div>

<p class="dated">Note: Last updated at {{ site.data.season_summary_latest | where: "stat", "update_time" | map: "value" | first }}. Read more <a href="https://github.com/stiles/dodgers/blob/main/README.md">about the data</a>.</p>


</div>

<script src="https://d3js.org/d3.v6.min.js"></script>
<script src="{{ '/assets/js/dashboard.js' | relative_url }}"></script>

