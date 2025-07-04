---
layout: default
title: Current roster | Los Angeles Dodgers player details
description: Full Dodgers roster, including active and 40-man players, with photos and details.
permalink: /roster/
canonical_url: https://dodgersdata.bot/roster/
header:
  og_image: /assets/images/meta_card.png
twitter:
  card: summary_large_image
---

<div class="container">
  <div class="minimal-header">
    <img src="{{ '/data/roster/avatars/placeholder-avatar.png' | absolute_url }}" alt="Dodgers Player" style="width: 50px; height: 50px; display: block; margin: 0 auto 20px auto; border-radius: 50%;" />
    <h1 class="minimal-headline">Who's on the roster?</h1>
    <p class="minimal-subhead">The team's active roster holds up to 26 players who can take the field in games. The 40-man roster includes those players but also prospects, injured starters or minor leaguers with contracts who are eligible to be called up. The latest breakdown, according to <a href="https://www.mlb.com/dodgers/roster">Major League Baseball</a>: </p>
  </div>

  <div class="tabs" id="roster-tabs">
    <button class="button-custom" data-tab="active">Active roster</button>
    <button class="button-custom" data-tab="forty">40-man roster</button>
  </div>

  <div id="roster-active" class="roster-tab-content">
    {% assign players = site.data.roster.dodgers_roster_current %}
    {% assign active_players = players | where: "is_active_roster", true %}
    {% assign position_groups = active_players | map: "position_group" | uniq %}
    {% for group in position_groups %}
      <h2 class="stat-group">{{ group }}</h2>
      <div class="roster-grid">
        {% assign group_players = active_players | where: "position_group", group %}
        {% for player in group_players %}
          {% assign slug = player.slug %}
          <div class="stat-card player-card">
            {% if player.is_active_roster %}
              <div class="player-flag player-flag-active">ACTIVE</div>
            {% elsif player.is_il %}
              <div class="player-flag player-flag-injured">INJURED</div>
            {% elsif player.is_minors %}
              <div class="player-flag player-flag-minors">MINORS</div>
            {% endif %}
            <img src="{{ '/data/roster/avatars/' | append: player.slug | append: '.png' | absolute_url }}" alt="{{ player.name }}" class="player-avatar" onerror="this.onerror=null;this.src='{{ '/data/roster/avatars/placeholder-avatar.png' | absolute_url }}';" />
            <div class="player-name">{{ player.name }}</div>
            <div class="player-details">{{ player.bat_throw }} | {{ player.height }}, {{ player.weight }} lbs</div>
            <div class="player-jersey">#{{ player.jersey }}</div>
          </div>
        {% endfor %}
      </div>
    {% endfor %}
  </div>

  <div id="roster-forty" class="roster-tab-content" style="display:none;">
    {% assign forty_players = players %}
    {% assign position_groups = forty_players | map: "position_group" | uniq %}
    {% for group in position_groups %}
      <h2 class="stat-group">{{ group }}</h2>
      <div class="roster-grid">
        {% assign group_players = forty_players | where: "position_group", group %}
        {% for player in group_players %}
          {% assign slug = player.slug %}
          <div class="stat-card player-card">
            {% if player.is_active_roster %}
              <div class="player-flag player-flag-active">ACTIVE</div>
            {% elsif player.is_il %}
              <div class="player-flag player-flag-injured">INJURED</div>
            {% elsif player.is_minors %}
              <div class="player-flag player-flag-minors">MINORS</div>
            {% endif %}
            <img src="{{ '/data/roster/avatars/' | append: player.slug | append: '.png' | absolute_url }}" alt="{{ player.name }}" class="player-avatar" onerror="this.onerror=null;this.src='{{ '/data/roster/avatars/placeholder-avatar.png' | absolute_url }}';" />
            <div class="player-name">{{ player.name }}</div>
            <div class="player-details">{{ player.bat_throw }} | {{ player.height }}, {{ player.weight }} lbs</div>
            <div class="player-jersey">#{{ player.jersey }}</div>
          </div>
        {% endfor %}
      </div>
    {% endfor %}
  </div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('#roster-tabs button');
    const tabContents = document.querySelectorAll('.roster-tab-content');
    const initialTab = tabs[0];

    // Set initial active state on page load
    if (initialTab) {
      initialTab.classList.add('active');
    }

    tabs.forEach(btn => {
      btn.addEventListener('click', function() {
        // Deactivate all tabs
        tabs.forEach(b => b.classList.remove('active'));
        tabContents.forEach(tc => tc.style.display = 'none');

        // Activate the clicked tab
        btn.classList.add('active');
        const targetContent = document.getElementById('roster-' + btn.dataset.tab);
        if (targetContent) {
          targetContent.style.display = 'block';
        }
      });
    });
  });
</script> 