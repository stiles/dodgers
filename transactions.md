---
layout: default
title: Dodgers Transactions
description: A log of recent Dodgers player transactions.
permalink: /transactions/
---

<div class="container">
  <div class="minimal-header">
  <img src="{{ '/data/roster/avatars/placeholder-avatar.png' | absolute_url }}" alt="Dodgers Player" style="width: 50px; height: 50px; display: block; margin: 0 auto 20px auto; border-radius: 50%;" />
    <h1 class="minimal-headline">Recent transactions</h1>
    <p class="minimal-subhead">A log of the team's last 100 player moves, according to <a href="https://www.mlb.com/dodgers/roster/transactions">Major League Baseball</a>: </p>
  </div>

  {% assign transactions = site.data.roster.dodgers_transactions_current %}
  {% assign players_roster = site.data.roster.dodgers_roster_current %}

  <div class="transactions-grid">
    {% for transaction in transactions %}
      <div class="stat-card transaction-card">
        <div class="transaction-date">{{ transaction.date | date: "%B %-d, %Y" }}</div>

        {% if transaction.players %}
          <div class="transaction-players-container">
            {% for player_name in transaction.players %}
              <div class="player-profile-transaction">
                <div class="player-name-transaction">{{ player_name }}</div>
                {% assign player_data = players_roster | where: "name", player_name | first %}
                {% if player_data.slug %}
                  <img src="{{ '/data/roster/avatars/' | append: player_data.slug | append: '.png' | absolute_url }}" alt="{{ player_name }}" class="player-avatar-transaction" title="{{ player_name }}" onerror="this.onerror=null;this.src='{{ '/data/roster/avatars/placeholder-avatar.png' | absolute_url }}';" />
                {% else %}
                  <img src="{{ '/data/roster/avatars/placeholder-avatar.png' | absolute_url }}" alt="{{ player_name }}" title="{{ player_name }}" class="player-avatar-transaction" />
                {% endif %}
              </div>
            {% endfor %}
          </div>
        {% endif %}

        <div class="transaction-description">
          {{ transaction.transaction }}
        </div>
      </div>
    {% endfor %}
  </div>
</div> 