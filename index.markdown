---
layout: default
title: LA Dodgers Data Bot - A dashboard explaining the Dodgers' season so far. 
permalink: /
---

<div class="container">

<div class="page-topper">
<div class="trend-icon">
    {% assign last_game_result_array = site.data.season_summary_latest | where: "stat", "last_game_result" %}
    {% assign last_game_result = last_game_result_array[0].value %}
    {% if last_game_result == 'win' %}
        <i class="fa-solid fa-arrow-trend-up" style="color: #005a9c;"></i>
    {% else %}
        <i class="fa-solid fa-arrow-trend-down" style="color: #ef3e42;"></i>
    {% endif %}
</div>
<h1 class="headline">{{ site.headline }}</h1>
<p class="subhead">
    {% assign summary_info = site.data.season_summary_latest | where: "stat", "summary" %}
    {% assign summary = summary_info[0].value %}
    {{ summary }}
</p>
</div>



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
<p class="chart-chatter">Since moving to LA, the Dodgers have won the World Series six times: 2020, 1988, 1981, 1965, 1963 and 1959. Compare this year's win trajectory with the past.</p>
<select id="year-select">
  <option>Previous seasons</option>
</select>
<div id="cumulative-wins-chart"></div>

<h3 class="visual-subhead">Standings: Games <span class="win">up</span> or <span class="loss">back</span></h3>
<div id="d3-container" style="width: 100%; padding-bottom: 20px;"></div>

<h2 class="stat-group">Team batting</h2>
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

<h2 class="stat-group">Player batting</h2>
<p class="chart-chatter">Darker shades represent <span class="win">better</span> performance.</p>
<div class="tables-container">
  <div class="table-wrapper">
      <h3 class="visual-subhead">Batting average and on-base and slugging percentages</h3>
      <table id="table-1" class="data-table">
          <thead>
              <tr>
                  <th>Player</th>
                  <th>Pos</th>
                  <th class="table-value">BA</th>
                  <th class="table-value">OB%</th>
                  <th class="table-value">SLG%</th>
              </tr>
          </thead>
          <tbody></tbody>
      </table>
  </div>
  <div class="table-wrapper">
      <h3 class="visual-subhead">Walks, home runs and strikeouts per plate appearance</h3>
      <table id="table-2" class="data-table">
          <thead>
              <tr>
                  <th>Player</th>
                  <th>PA</th>
                  <th class="table-value">BB/A</th>
                  <th class="table-value">HR/A</th>
                  <th class="table-value">SO/A</th>
              </tr>
          </thead>
          <tbody></tbody>
      </table>
  </div>

<div id="event-selection">
  <label for="event-select">Every plate appearance, with outcome. Select one:</label>
  <select id="event-select"></select>
</div>
<div id="barcode-chart">
  <svg></svg>
</div>







 <p class="note">Note: Tables and chart include top-10 batters by plate appearances. </p>
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

<div class="large-chart-container">
<h3 class="visual-subhead">Team <span class="win">ERA</span> over season: Then and now</h3>
<div id="cumulative-era-chart"></div>
</div>

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
          <h3 class="visual-subhead">Next 10</h3>
          <table id="next-games" class="data-table">
              <thead>
                  <tr>
                      <th>Date</th>
                      <th>Opponent</th>
                      <th>Location</th>
                      <th>Time (PT)</th>
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

  <p class="dated">Notes: Last updated {{ site.data.season_summary_latest | where: "stat", "update_time" | map: "value" | first }}. More <a href="https://github.com/stiles/dodgers/blob/main/README.md">about the data</a>.</p>
  
</div>

<script src="https://d3js.org/d3.v6.min.js"></script>
<script src="{{ '/assets/js/dashboard.js' | relative_url }}"></script>