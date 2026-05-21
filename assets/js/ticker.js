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

  // Rebuild the track with the shuffled set, then a clone of it so the
  // CSS marquee (translateX 0 -> -50%) loops seamlessly.
  var frag = document.createDocumentFragment();
  groups.forEach(function (g) {
    g.forEach(function (node) { frag.appendChild(node); });
  });

  // Clone the freshly-shuffled set before we attach the original, so the
  // cloned nodes are identical to the originals.
  var clones = [];
  Array.from(frag.children).forEach(function (node) {
    clones.push(node.cloneNode(true));
  });

  track.innerHTML = '';
  track.appendChild(frag);
  clones.forEach(function (node) { track.appendChild(node); });
})();
