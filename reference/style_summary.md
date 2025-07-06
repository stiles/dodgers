# Dodgers Data Bot design/style guide

This guide summarizes the visual design principles and implementation details for the **Dodgers Data Bot** project to guide with **CSS**, **D3** or **Python charting libraries**.

---

## Design philosophy

1. **Data-driven clarity**  
   Let baseball statistics tell their story clearly. Minimize decoration that doesn't serve the data.

2. **Dodgers brand integration**  
   Use team colors purposefully to create brand connection while maintaining readability.

3. **Mobile-first responsiveness**  
   Charts and layouts must work seamlessly from mobile to desktop.

4. **Accessible typography**  
   Clear hierarchy using Roboto and Roboto Slab families for optimal readability.

5. **Honest representation**  
   Zero baselines on bar charts, consistent scales, and transparent data sourcing.

6. **Progressive disclosure**  
   Complex data broken into digestible sections with clear visual hierarchy.

---

## 🎨 Color system

### Brand colors
- **Dodger Blue (Primary):** `#005A9C` - Main brand color for highlights, buttons, current year data
- **Dodger Red (Secondary):** `#EF3E42` - Used for losses, negative trends, alerts
- **Dodger Silver:** `#BFC0BF` - Supporting neutral color

### Functional colors
- **Text Primary:** `#444` - Main body text, headlines
- **Text Secondary:** `#666` - Chart titles, labels
- **Text Muted:** `#777` - Axis labels, annotations
- **Text Light:** `#999` - Notes, sources, metadata
- **Text Subtle:** `#a2a2a2` - Chart annotations, light text
- **Background:** `#FEFEFE` - Chart backgrounds, cards
- **Borders:** `#ddd` - Table borders, card borders
- **Grid Lines:** `#e9e9e9` - Chart axes, subtle dividers

### Status colors
- **Win/Success:** `#005A9C` (Dodger Blue)
- **Loss/Alert:** `#EF3E42` (Dodger Red)
- **Neutral/Past Data:** `#ccc` - Historical comparison lines

### Chart-specific colors
- **Good Calls (Umpire):** `#53A796` - Correct strike calls
- **Bad Calls (Umpire):** `#F18851` - Incorrect strike calls
- **Trend Up:** `#38761d` - Positive performance indicators
- **Trend Down:** `#cc0000` - Negative performance indicators

---

## 📐 Typography

### Font families
- **Headlines/Display:** `'Roboto Slab', serif` - Used for main headlines, chart titles, player names
- **Body/UI:** `'Roboto', sans-serif` - Used for body text, annotations, labels, buttons

### Typography scale

| Element | Font | Size | Weight | Color | Usage |
|---------|------|------|--------|-------|-------|
| **Main Headline** | Roboto Slab | 100px (50px mobile) | 700 | #444 | Page title |
| **Hero Headline** | Roboto Slab | 72px (48px mobile) | 700 | white | Hero sections |
| **Section Headers** | Roboto Slab | 1.3em | normal | #444 | h2.stat-group |
| **Chart Titles** | Roboto Slab | 1em | normal | #666 | h3.visual-subhead |
| **Card Values** | Roboto Slab | 48px | 700 | #005A9C | Stat card numbers |
| **Subheads** | Roboto | 20px (16px mobile) | normal | #444 | Descriptive text |
| **Body Text** | Roboto | 16px | normal | #444 | General content |
| **Chart Annotations** | Roboto | 12px | normal | #777 | .anno-dark |
| **Light Annotations** | Roboto | 12px | normal | #a2a2a2 | .anno |
| **Player Names** | Roboto Slab | 14px | normal | #666 | .anno-player |
| **Dodgers Highlights** | Roboto Slab | 14px | bold | #005A9C | .anno-dodgers |
| **Notes/Sources** | Roboto | 12px | normal | #999 | .note |

---

## 📊 Chart design specifications

### Layout
- **Container max-width:** 900px
- **Mobile padding:** 15px
- **Chart margins:** 
  - Desktop: `{top: 20, right: 20, bottom: 40, left: 50}`
  - Mobile: `{top: 20, right: 20, bottom: 50, left: 40}`

### Lines and strokes
- **Current year data:** 2-3px, `#005A9C`
- **Historical data:** 0.5px, `#ccc`
- **Selected comparison:** 1.5px, `#EF3E42`
- **Axis lines:** `#e9e9e9`
- **Grid lines:** `#e9e9e9`
- **Zero baseline:** 1px, `#222`

### Interactive elements
- **Hover states:** Subtle box-shadow increase
- **Buttons:** GitHub-style with `#FAFBFC` background
- **Active states:** `#005A9C` background, white text

---

## 🏗 Component patterns

### Stat cards
```css
.stat-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 24px 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}
```

### Data tables
```css
.data-table {
  border-collapse: collapse;
  font-family: 'Roboto', sans-serif;
  font-size: 12px;
}

.data-table th {
  background-color: #fff;
  border-bottom: 1px solid #999;
  font-family: 'Roboto Slab', serif;
  font-size: 0.9em;
}
```

### Chart containers
- Use viewBox for responsive SVGs
- Consistent margin conventions
- Mobile-first breakpoint at 767px

---

## 📱 Responsive design

### Breakpoints
- **Mobile:** max-width 767px
- **Desktop:** min-width 768px

### Mobile adaptations
- Headlines: 50px → 100px
- Subheads: 16px → 20px
- Increased touch targets
- Simplified chart annotations
- Stacked layouts for tables

---

## 🎯 Chart-specific guidelines

### Line charts
- Current season: Bold blue line (`#005A9C`, 2-3px)
- Historical data: Light gray (`#ccc`, 0.5px)
- Comparison year: Red (`#EF3E42`, 1.5px)
- Smooth curves using `d3.curveMonotoneX`

### Bar charts
- Single color preference
- Use Dodger Blue for positive metrics
- Use Dodger Red sparingly for losses/negative
- Include zero baseline

### Tables
- Conditional formatting with blue color scales
- Heat mapping from `#cce5ff` (light) to `#005a9c` (dark)
- High contrast text based on background

### Annotations
- Direct labeling preferred over legends
- White stroke outline for text over charts
- Position labels to avoid overlapping data

---

## 🧑‍💻 D3.js implementation patterns

### Color scales
```javascript
const teamColors = {
  primary: '#005A9C',
  secondary: '#EF3E42', 
  neutral: '#ccc',
  success: '#38761d',
  warning: '#cc0000'
};
```

### Text styling
```javascript
svg.append('text')
  .attr('class', 'anno-dark')
  .style('font-family', 'Roboto, sans-serif')
  .style('font-size', '12px')
  .style('fill', '#777');
```

### Responsive patterns
```javascript
const isMobile = window.innerWidth <= 767;
const margin = isMobile 
  ? { top: 20, right: 20, bottom: 50, left: 40 }
  : { top: 20, right: 20, bottom: 40, left: 50 };
```

---

## 🎨 CSS utility classes

### Text styling
- `.anno` - Light annotations (#a2a2a2)
- `.anno-dark` - Standard annotations (#777)
- `.anno-player` - Player names (Roboto Slab, #666)
- `.anno-dodgers` - Team highlights (Roboto Slab, bold, #005A9C)

### Status indicators
- `.win` - Success states (background: #005A9C, white text)
- `.loss` - Alert states (background: #EF3E42, white text)
- `.winning` - Text color: #005A9C
- `.losing` - Text color: #EF3E42

### Layout helpers
- `.container` - Max-width 900px, centered
- `.grid-container` - Flex grid with responsive behavior
- `.table-wrapper` - Responsive table containers

---

## 📈 Python/Matplotlib styling

```python
import matplotlib.pyplot as plt

# Dodgers theme
plt.rcParams.update({
    "font.family": "DejaVu Sans",  # Substitute for Roboto
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelcolor": "#777",
    "xtick.color": "#777", 
    "ytick.color": "#777",
    "text.color": "#444",
    "axes.edgecolor": "#e9e9e9",
    "axes.linewidth": 0.5,
    "figure.facecolor": "#FEFEFE",
    "axes.facecolor": "#FEFEFE",
    "grid.color": "#e9e9e9",
    "grid.linewidth": 0.5
})

# Team colors
DODGER_BLUE = '#005A9C'
DODGER_RED = '#EF3E42'
NEUTRAL_GRAY = '#ccc'
```

---

## Baseball-specific conventions

### Team representation
- Current season: Always Dodger Blue
- Historical comparisons: Light gray
- Selected comparison: Dodger Red
- Wins: Blue background with white text
- Losses: Red background with white text

### Data integrity
- Always include data sources in notes or in readme
- Use "Note:" prefix for methodology explanations
- Transparent about projections vs. actual data

### Terminology
- Use standard baseball abbreviations (HR, RBI, ERA, etc.)
- "Games back" not "games behind"
- Consistent date formatting: "Month Day, Year"


