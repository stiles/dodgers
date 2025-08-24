---
layout: default
title: "Los Angeles Dodgers stats dashboard | Updated data & analysis"
description: "An auto-updating team dashboard that answers the question: How are the Dodgers doing?"
permalink: /
canonical_url: https://dodgersdata.bot/
header:
  og_image: /assets/images/meta_card.png
twitter:
  card: summary_large_image
---

<div class="container">

<div class="minimal-header">
  {% assign last_game_result_array = site.data.season_summary_latest | where: "stat", "last_game_result" %}
  {% assign last_game_result = last_game_result_array[0].value %}
  <div class="minimal-trend-icon">
    {% if last_game_result == 'win' %}
        <i class="fa-solid fa-arrow-trend-up"></i>
    {% else %}
        <i class="fa-solid fa-arrow-trend-down"></i>
    {% endif %}
  </div>
  <h1 class="minimal-headline">{{ site.headline }}</h1>
  <p class="minimal-subhead">
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
        <div class="stat-card mb-4">
          <div class="stat-card-label">{{ item.stat_label }}</div>
          <div class="stat-card-value">{{ item.value }}</div>
          <p class="stat-card-context">{{ item.context_value_label }}: {{ item.context_value }}</p>
        </div>
      </div>
      {% endif %}
    {% endfor %}
  </div>

<h3 class="visual-subhead">Projected <span class="win">wins</span> this season</h3>
<p class="chart-chatter">This chart shows the Dodgers' actual <span class="underline-wins">wins</span> so far, the projected <span class="underline-mean-projection">mean</span> number of final wins and the 95% <span class="highlight-ci">confidence interval</span> around that projection.</p>
<div id="wins-projection-chart-ci" class="chart-container"></div>
<p class="note">Note: The projection is based on 10,000 simulations. For games played, it shows actual wins. For future games, it simulates outcomes by randomly drawing from the Dodgers' win/loss results so far this season, then calculates the mean and a 95% confidence range.</p>

<h3 class="visual-subhead">Cumulative <span class="win">wins</span>: Then and now</h3>
<p class="chart-chatter">Since moving to LA, the Dodgers have won the World Series seven times: 2024, 2020, 1988, 1981, 1965, 1963 and 1959. Compare this year's win trajectory with the past.</p>
<select id="year-select">
  <option>Previous seasons</option>
</select>
<div id="cumulative-wins-chart"></div>

<h3 class="visual-subhead">Standings: Games <span class="win">up</span> or <span class="loss">back</span></h3>
<div id="d3-container" style="width: 100%; padding-bottom: 20px;"></div>

{% assign current_year_str = site.time | date: '%Y' %}
{% assign dynamic_filename_key = "all_teams_standings_metrics_" | append: current_year_str %}

{% comment %} Try to load current year's data using the dynamic filename key {% endcomment %}
{% assign standings_data = site.data.standings[dynamic_filename_key] %}

{% comment %} Fallback to 2024 data if current year's data is not found.
    This also covers the case where the dynamic key was for 2024 but didn't load. {% endcomment %}
{% if standings_data == nil %}
  {% assign standings_data = site.data.standings.all_teams_standings_metrics_2024 %}
{% endif %}

{% comment %} If all potential data sources are nil, default to an empty array to prevent errors. {% endcomment %}
{% if standings_data == nil %}
  {% assign standings_data = "" | split: "" %}
{% endif %}

{% assign nl_teams = standings_data | where_exp: "item", "item.league_name == 'National League'" %}
{% if nl_teams == nil %} {% assign nl_teams = "" | split: "" %} {% endif %}

{% assign nl_west = nl_teams | where_exp: "item", "item.division_name == 'National League West'" | sort: "division_rank" %}
{% assign nl_central = nl_teams | where_exp: "item", "item.division_name == 'National League Central'" | sort: "division_rank" %}
{% assign nl_east = nl_teams | where_exp: "item", "item.division_name == 'National League East'" | sort: "division_rank" %}

<h3 class="visual-subhead">National League standings by division</h3>
<div class="tables-container standings-tables">
  <div class="table-wrapper">
    <h3 class="visual-subhead">NL West</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>Team</th>
          <th>W%</th>
          <th>GB</th>
        </tr>
      </thead>
      <tbody>
        {% for team in nl_west %}
        <tr {% if team.team_name == "Los Angeles Dodgers" %}class="dodgers-row"{% endif %}>
          <td>{{ team.team_name }}</td>
          <td>{{ team.winning_percentage }}</td>
          <td>{{ team.games_back }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="table-wrapper">
    <h3 class="visual-subhead">NL Central</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>Team</th>
          <th>W%</th>
          <th>GB</th>
        </tr>
      </thead>
      <tbody>
        {% for team in nl_central %}
        <tr>
          <td>{{ team.team_name }}</td>
          <td>{{ team.winning_percentage }}</td>
          <td>{{ team.games_back }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="table-wrapper">
    <h3 class="visual-subhead">NL East</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>Team</th>
          <th>W%</th>
          <th>GB</th>
        </tr>
      </thead>
      <tbody>
        {% for team in nl_east %}
        <tr>
         <td>{{ team.team_name }}</td>
          <td>{{ team.winning_percentage }}</td>
          <td>{{ team.games_back }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<h2 class="stat-group">Team batting</h2>
  <div class="row">
    {% for item in site.data.season_summary_latest %}
      {% if item.category == 'batting' %}
      <div class="col-md-4">
        <div class="stat-card mb-4">
          <div class="stat-card-label">{{ item.stat_label }}</div>
          <div class="stat-card-value">{{ item.value }}</div>
          <p class="stat-card-context">{{ item.context_value_label }}: {{ item.context_value }}</p>
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
   <p class="note">Note: Tables and charts include top batters by plate appearances.</p>
</div>

  <h3 class="visual-subhead">Recent form: Expected weighted on-base average</h3>
  <p class="chart-chatter">Rolling 100-plate appearance <span class='anno-xwoba'>xwOBA</span> for each Dodgers batter compared to the <span class='anno-mean'>league average</span>. This stat predicts a player's offensive contributions based on the quality of contact they make with the ball.</p>
  <div id="xwoba-grid" class="xwoba-grid-container">
  </div>

  <h2 class="stat-group">Shohei stats</h2>

  <h3 class="visual-subhead">50-50 trend</h3>
  <p id="shohei-comparison-subhead" class="chart-chatter"></p>
  <div class="charts-container">
    <div id="shohei-homers-chart" class="small-chart-container"></div>
    <div id="shohei-sb-chart" class="small-chart-container"></div>
  </div>

  <h2 class="stat-group">Umpire scorecard (batting)</h2>
<div class="scorecard-row">
  <div class="scorecard-left">
  <h3 class="visual-subhead">Strike zone analysis</h3>
  <p class="chart-chatter">How often do Dodgers batters get called strikes on pitches outside the strike zone? Correctly called <span style="background-color: #53A796; color: #fff; font-weight: bold; padding: 1px 6px; border-radius: 5px;">strikes</span> vs. pitches that were actually <span style="background-color: #F18851; color: #fff; font-weight: bold; padding: 1px 6px; border-radius: 5px;">balls</span>:</p>
    <div id="umpire-scorecard-chart"></div>
  </div>
  <div class="scorecard-right">
    <h3 class="visual-subhead">Worst calls of the season</h3>
    <div id="umpire-worst-calls"></div>
  </div>
</div>
 <p class="note">Note: Strike zone calls are determined by Baseball Savant and <a href="https://github.com/stiles/dodgers/blob/main/scripts/20_fetch_game_pitches.py">collected</a> after each game from its gamefeed API. Download the data <a href="https://stilesdata.com/dodgers/data/pitches/dodgers_pitches_2025.json">here</a>.</p>
  

  <h2 class="stat-group">Pitching</h2>
  <div class="row">
    {% for item in site.data.season_summary_latest %}
      {% if item.category == 'pitching' %}
      <div class="col-md-4">
        <div class="stat-card mb-4">
          <div class="stat-card-label">{{ item.stat_label }}</div>
          <div class="stat-card-value">{{ item.value }}</div>
          <p class="stat-card-context">{{ item.context_value_label }}: {{ item.context_value }}</p>
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

  <h2 class="stat-group">Umpire scorecard (pitching)</h2>
<div class="scorecard-row">
  <div class="scorecard-left">
  <h3 class="visual-subhead">Pitching strike zone analysis</h3>
  <p class="chart-chatter">How often are Dodgers pitchers charged with <span style="background-color: #F18851; color: #fff; font-weight: bold; padding: 1px 6px; border-radius: 5px;">balls</span> that were actually <span style="background-color: #53A796; color: #fff; font-weight: bold; padding: 1px 6px; border-radius: 5px;">strikes</span>?</p>
    <div id="umpire-scorecard-pitching-chart"></div>
  </div>
  <div class="scorecard-right">
    <h3 class="visual-subhead">Worst calls against Dodgers pitchers</h3>
    <div id="umpire-worst-calls-pitching"></div>
  </div>
</div>
 <p class="note">Note: Strike zone calls are determined by Baseball Savant and <a href="https://github.com/stiles/dodgers/blob/main/scripts/20_fetch_game_pitches.py">collected</a> after each game from its gamefeed API. Download the data <a href="https://stilesdata.com/dodgers/data/pitches/dodgers_pitches_thrown_2025.json">here</a>.</p>

  <h2 class="stat-group">Schedule</h2>
    <div id="schedule-section" class="schedule-tables">
      <div class="table-wrapper">
          <h3 class="visual-subhead">Last 10 games</h3>
          <table id="last-games" class="data-table">
              <thead>
                  <tr>
                      <th>Date</th>
                      <th>Opponent</th>
                      <th>Place</th>
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
                      <th>Place</th>
                      <th>Time PT</th>
                  </tr>
              </thead>
              <tbody></tbody>
          </table>
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

<script src="https://d3js.org/d3.v6.min.js"></script>
<script src="{{ '/assets/js/dashboard.js' | relative_url }}"></script>

<style>
@media (max-width: 767px) {
  .row {
    display: block;
  }
  .small-chart-container {
    width: 100%;
    margin-bottom: 30px;
  }
}

/* Desktop - force equal width distribution */
@media (min-width: 901px) {
  #schedule-section {
    display: flex !important;
    gap: 20px !important;
    justify-content: space-between !important;
  }
  #schedule-section .table-wrapper {
    flex: 1 1 calc(50% - 10px) !important;
    width: calc(50% - 10px) !important;
    max-width: calc(50% - 10px) !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
  #schedule-section .table-wrapper table {
    width: 100% !important;
    table-layout: fixed !important;
  }
}

@media (max-width: 900px) {
  #schedule-section {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
  }
  #schedule-section .table-wrapper {
    display: block !important;
    width: 100% !important;
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 0 20px 0 !important;
    background: transparent !important;
    border-radius: 0 !important;
    box-sizing: border-box !important;
  }
  #schedule-section .table-wrapper:last-child {
    margin-bottom: 0 !important;
  }
  #last-games,
  #next-games {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 100% !important;
    margin: 0 !important;
    table-layout: fixed !important;
    box-sizing: border-box !important;
  }
  #last-games *,
  #next-games * {
    box-sizing: border-box !important;
  }
  /* Force override any external CSS */
  body #schedule-section table {
    width: 100% !important;
    max-width: 100% !important;
  }
  #schedule-section h3.visual-subhead {
    margin: 15px 0 10px 0 !important;
  }
  #schedule-section h3.visual-subhead:first-child {
    margin-top: 0 !important;
  }
}
</style>