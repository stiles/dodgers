---
layout: default
title: LA Dodgers Data Bot - A dashboard explaining the Dodgers' season so far. 
permalink: /
---

<div class="container">

<div class="page-topper">
  <h1 class="headline">{{ site.headline }}</h1>
  <p class="subhead">{{ site.data.season_summary_latest | where: "stat", "summary" | map: "value" | first }} </p>
<div>



<div class="container mt-4">
<h2 class="stat-group">Performance and standings</h2>
<h3 class="visual-subhead"><span class="win">Wins</span>, <span class="loss">losses</span> and run differential</h3>
<div id="chart-container" class="chart-container" style="position: relative;">
    <div id="results-chart"></div>
</div>

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
  <h3 class="visual-subhead">Cumulative <span class="win">wins</span>: Then and now</h3>

<!-- <button id="toggle-view">Toggle: Just World Series wins</button> -->
<!-- <button id="toggle-view" class="button-custom" role="button">Toggle: Just World Series wins</button> -->
<div id="cumulative-wins-chart"></div>

<h3 class="visual-subhead">Standings: Games <span class="win">up</span> or <span class="loss">back</span></h3>
<div id="d3-container" style="width: 100%; padding-bottom: 20px;"></div>

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

<div class="small-chart-container">
  <h3 class="visual-subhead">Cumulative <span class="win">doubles</span></h3>
  <div id="cumulative-doubles-chart" class="small-chart"></div>
</div>

<div class="small-chart-container">
  <h3 class="visual-subhead">Cumulative <span class="win">home runs</span></h3>
  <div id="cumulative-homers-chart" class="small-chart"></div>
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

<h3 class="visual-subhead">Team <span class="win">ERA</span> over season: Then and now</h3>
<div id="cumulative-era-chart"></div>


<div class="small-chart-container">
  <h3 class="visual-subhead">Cumulative <span class="win">strikeouts</span></h3>
  <div id="cumulative-strikeouts-chart" class="small-chart"></div>
</div>

<div class="small-chart-container">
  <h3 class="visual-subhead">Cumulative <span class="win">hits</span> allowed</h3>
  <div id="cumulative-hits-chart" class="small-chart"></div>
</div>

<h2 class="stat-group">Schedule</h2>
  <div class="tables-container">
    <div class="table-wrapper">
        <h3 class="visual-subhead">Last 10 games</h3>
        <table id="last-games" class="data-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Opponent</th>
                    <th>Location</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
    <div class="table-wrapper">
        <h3 class="visual-subhead">Next 10 games</h3>
        <table id="next-games" class="data-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Opponent</th>
                    <th>Location</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>
  </div>

</div>

<h2 class="stat-group">Fan support</h2>
<p id="max-attendance-info"></p>
<div class="tables-container">
    <div class="table-wrapper">
        <h3 class="visual-subhead">National League</h3>
        <table id="nl-table" class="data-table"></table>
    </div>
    <div class="table-wrapper">
        <h3 class="visual-subhead">American League</h3>
        <table id="al-table" class="data-table"></table>
    </div>
</div>


</div>



<p class="dated">Notes: Last updated {{ site.data.season_summary_latest | where: "stat", "update_time" | map: "value" | first }}. More <a href="https://github.com/stiles/dodgers/blob/main/README.md">about the data</a>.</p>


</div>

<script src="https://d3js.org/d3.v6.min.js"></script>
<script src="{{ '/assets/js/dashboard.js' | relative_url }}"></script>