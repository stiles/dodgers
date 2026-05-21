(function () {
  'use strict';

  var track = document.querySelector('.news-ticker__track');
  if (!track) return;

  // Group each item with its trailing separator so they stay together when shuffled.
  var children = Array.from(track.children);
  var groups = [];
  for (var i = 0; i < children.length; i++) {
    var el = children[i];
    if (!el.classList.contains('news-ticker__item')) continue;
    var group = [el];
    var next = children[i + 1];
    if (next && next.classList.contains('news-ticker__sep')) {
      group.push(next);
      i++;
    }
    groups.push(group);
  }

  if (groups.length < 2) return; // Nothing meaningful to shuffle.

  // Fisher-Yates shuffle.
  for (var j = groups.length - 1; j > 0; j--) {
    var k = Math.floor(Math.random() * (j + 1));
    var tmp = groups[j];
    groups[j] = groups[k];
    groups[k] = tmp;
  }

  // Clear track and rebuild with shuffled set plus a clone so the
  // CSS marquee (translateX 0 -> -50%) loops seamlessly.
  track.innerHTML = '';
  
  // Append the shuffled groups
  groups.forEach(function (g) {
    g.forEach(function (node) { track.appendChild(node); });
  });

  // Clone all nodes we just appended (must do this after appending)
  var allNodes = Array.from(track.children);
  allNodes.forEach(function (node) {
    track.appendChild(node.cloneNode(true));
  });
})();
