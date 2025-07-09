// Custom mobile navigation for screens under 500px
function initMobileNavigation() {
  // Only initialize on mobile screens
  if (window.innerWidth > 500) return;
  
  const masthead = document.querySelector('.masthead');
  const greedyNav = document.querySelector('.greedy-nav');
  const visibleLinks = document.querySelector('.visible-links');
  
  if (!masthead || !greedyNav || !visibleLinks) return;
  
  // Create custom mobile menu if it doesn't exist
  let mobileMenu = document.querySelector('.custom-mobile-menu');
  if (!mobileMenu) {
    mobileMenu = document.createElement('div');
    mobileMenu.className = 'custom-mobile-menu';
    
    const menuList = document.createElement('ul');
    
    // Add navigation links to mobile menu
    const navLinks = [
      { title: 'Team', url: '/roster/' },
      { title: 'Moves', url: '/transactions/' },
      { title: 'About', url: '/about/' }
    ];
    
    navLinks.forEach(link => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = link.url;
      a.textContent = link.title;
      li.appendChild(a);
      menuList.appendChild(li);
    });
    
    mobileMenu.appendChild(menuList);
    greedyNav.appendChild(mobileMenu);
  }
  
  // Add click handler to the custom toggle (CSS pseudo-element)
  greedyNav.addEventListener('click', function(e) {
    // Check if click is on the right side where our toggle is
    const rect = greedyNav.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const toggleArea = rect.width - 50; // 50px from right edge
    
    if (clickX > toggleArea) {
      e.preventDefault();
      mobileMenu.classList.toggle('show');
    }
  });
  
  // Close menu when clicking outside
  document.addEventListener('click', function(e) {
    if (!greedyNav.contains(e.target)) {
      mobileMenu.classList.remove('show');
    }
  });
  
  // Close menu when clicking a link
  mobileMenu.addEventListener('click', function(e) {
    if (e.target.tagName === 'A') {
      mobileMenu.classList.remove('show');
    }
  });
}

// Initialize mobile navigation when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  initMobileNavigation();
  
  // Re-initialize on window resize
  window.addEventListener('resize', function() {
    if (window.innerWidth <= 500) {
      initMobileNavigation();
    }
  });
}); 