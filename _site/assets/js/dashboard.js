// Remove DOM error prevention code
// document.addEventListener('DOMContentLoaded', function() {
//   // Intercept querySelectorAll calls on null elements
//   const originalQuerySelectorAll = Element.prototype.querySelectorAll;
//   Element.prototype.querySelectorAll = function(...args) {
//     try {
//       return originalQuerySelectorAll.apply(this, args);
//     } catch (e) {
//       console.warn('Prevented querySelectorAll error:', e);
//       return [];
//     }
//   };
//   
//   // Disable any specific element interactions that might be causing issues
//   // This is a more targeted approach if you know what element might be missing
//   if (!document.getElementById('barcode-chart')) {
//     // Create a dummy element to prevent errors
//     const dummy = document.createElement('div');
//     dummy.id = 'barcode-chart';
//     dummy.style.display = 'none';
//     document.body.appendChild(dummy);
//   }
// });

// Games back line chart

async function fetchData() {
  try {
    const response = await d3.json(
      'https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present_optimized.json'
    );
    // Group data by year, converting the year to a string for consistency
    const groupedByYear = d3.group(response, (d) => d.year.toString());
    renderChart(groupedByYear);
  } catch (error) {
    console.error('Failed to fetch data:', error);
  }
}

function renderChart(data) {
  // Dynamically get the current year as a string
  const currentYear = new Date().getFullYear().toString();
  const isMobile = window.innerWidth <= 767; // Example breakpoint for mobile devices
  const margin = isMobile 
    ? { top: 30, right: 20, bottom: 70, left: 70 }  // Smaller margins for mobile
    : { top: 30, right: 20, bottom: 60, left: 70 }; // Larger margins for desktop
  const container = d3.select('#d3-container');
  const containerWidth = container.node().getBoundingClientRect().width;
  const width = containerWidth - margin.left - margin.right;
  const height = isMobile 
    ? Math.round(width * 1) - margin.top - margin.bottom  // Taller for mobile
    : Math.round(width * 0.5) - margin.top - margin.bottom; // 2x1 ratio for desktop

  const svg = container
    .append('svg')
    .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
    .append('g')
    .attr('transform', `translate(${margin.left}, ${margin.top})`);

  const xScale = d3.scaleLinear()
    .domain([0, 166])
    .range([0, width]);

  const yScale = d3.scaleLinear()
    .domain([
      d3.min(Array.from(data.values()).flat(), (d) => d.gb),
      d3.max(Array.from(data.values()).flat(), (d) => d.gb)
    ])
    .range([height, 0]);

  const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('d'));
  const yAxis = d3.axisLeft(yScale).ticks(6);
  
  svg.append('g')
    .attr('transform', `translate(0, ${height})`)
    .call(xAxis);
  
  svg.append('g').call(yAxis);
  
  // Add zero line
  svg.append('line')
    .attr('x1', 0)
    .attr('x2', width)
    .attr('y1', yScale(0))
    .attr('y2', yScale(0))
    .attr('stroke', '#222')
    .attr('stroke-width', 1);

  // X-axis Label
  svg.append("text")
    .attr("text-anchor", "middle")
    .attr('class', 'anno-dark')
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .text("Game number in season");
  
  // Y-axis Label
  svg.append("text")
    .attr("text-anchor", "middle")
    .attr('class', 'anno-dark')
    .attr("transform", "rotate(-90)")
    .attr("y", -margin.left + 20)
    .attr("x", -height / 2)
    .text("Games up/back");

  // Append axes to SVG
  svg.append('g')
    .attr('transform', `translate(0, ${height})`)
    .call(xAxis)
    .selectAll('line')
    .style('stroke', '#ddd');

  svg.append('g').call(yAxis).selectAll('line').style('stroke', '#ddd');
  svg.selectAll('.domain').style('stroke', '#e9e9e9');

  const line = d3.line()
    .x((d) => xScale(d.gm))
    .y((d) => yScale(d.gb))
    .curve(d3.curveMonotoneX);

  // Draw all lines except the current year first
  const allLinesExceptCurrent = Array.from(data.entries()).filter(
    (d) => d[0] !== currentYear
  );
  svg.selectAll('.line')
    .data(allLinesExceptCurrent, (d) => d[0])
    .enter()
    .append('path')
    .attr('class', 'line')
    .attr('d', (d) => line(d[1]))
    .style('fill', 'none')
    .style('stroke', '#ccc')
    .style('stroke-width', 0.5);

  // Draw the current year line
  const lineCurrent = Array.from(data.entries()).filter((d) => d[0] === currentYear);
  svg.selectAll('.line-current')
    .data(lineCurrent, (d) => d[0])
    .enter()
    .append('path')
    .attr('class', 'line')
    .attr('d', (d) => line(d[1]))
    .style('fill', 'none')
    .style('stroke', '#005A9C')
    .style('stroke-width', 2);

  // Add a horizontal line at y = 0
  svg.append('line')
    .attr('x1', 0)
    .attr('x2', width)
    .attr('y1', yScale(0))
    .attr('y2', yScale(0))
    .attr('stroke', '#222')
    .attr('stroke-width', 1);

  // Add the 'Leading' annotation
  svg.append('text')
    .attr('x', isMobile ? xScale(75) : xScale(70))
    .attr('y', yScale(0) - 10)
    .text('Leading ↑')
    .attr('class', 'anno-dark')
    .style('stroke', '#fff')
    .style('stroke-width', '4px')
    .style('stroke-linejoin', 'round')
    .attr('text-anchor', 'start')
    .style('paint-order', 'stroke')
    .clone(true)
    .style('stroke', 'none');

  // Add the 'Past' annotation
  svg.append('text')
    .attr('x', isMobile ? xScale(80) : xScale(110))
    .attr('y', yScale(22))
    .attr('class', 'anno')
    .text(`Past: 1958-${parseInt(currentYear) - 1}`)
    .attr('text-anchor', 'start');

  // Get the last data point for the current year safely
  const currentDataArray = data.get(currentYear);
  if (currentDataArray && currentDataArray.length > 0) {
    // Ensure data is sorted by game number before taking the last point
    currentDataArray.sort((a, b) => a.gm - b.gm);
    const lastDataCurrent = currentDataArray.slice(-1)[0];

    svg.append('text')
      .attr('x', xScale(lastDataCurrent.gm + 1)) // Reduced horizontal offset
      .attr('y', yScale(lastDataCurrent.gb) - 10)
      .text(currentYear)
      .attr('class', 'anno-dodgers')
      .style('stroke', '#fff')
      .style('stroke-width', '4px')
      .style('stroke-linejoin', 'round')
      .attr('text-anchor', 'start')
      .style('paint-order', 'stroke')
      .clone(true)
      .style('stroke', 'none');

    svg.append('text')
      .attr('x', xScale(lastDataCurrent.gm + 1.5)) // Reduced horizontal offset
      .attr('y', yScale(lastDataCurrent.gb) + 1)
      .text(() => {
          const gb = lastDataCurrent.gb;
          if (gb > 0) {
              return `${gb} games up`;
          } else if (gb < 0) {
              return `${Math.abs(gb)} games back`;
          } else {
              return 'Even';
          }
      })
      .attr('class', 'anno-dark')
      .style('stroke', '#fff')
      .style('stroke-width', '4px')
      .style('stroke-linejoin', 'round')
      .attr('text-anchor', 'start')
      .style('paint-order', 'stroke')
      .clone(true)
      .style('stroke', 'none');
  }
}

fetchData();






// Wins, losses, run differential column chart

async function fetchGameData() {
  try {
    const response = await d3.json('https://stilesdata.com/dodgers/data/standings/dodgers_wins_losses_current.json');
    response.reverse(); // Reverse the array to start from the beginning of the season
    renderRunDiffChart(response);
  } catch (error) {
    console.error('Failed to fetch game data:', error);
  }
}

function renderRunDiffChart(data) {
  const isMobile = window.innerWidth <= 767;
  const margin = isMobile ? { top: 20, right: 20, bottom: 50, left: 40 } : { top: 20, right: 20, bottom: 40, left: 50 };
  const container = d3.select('#results-chart');
  if (container.empty()) {
      console.error("Container #results-chart not found.");
      return;
  }
  container.html(""); // Clear previous chart

  const containerWidth = container.node().getBoundingClientRect().width;
  const width = containerWidth - margin.left - margin.right;
  const height = 200 - margin.top - margin.bottom; // Keeping height compact as it was

  const svg = container.append('svg')
    .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`) // Use viewBox
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const xScale = d3
    .scaleBand()
    .range([0, width])
    .padding(0.1)
    .domain(d3.range(1, 163)); // Assuming max 162 games

  const minRunDiff = d3.min(data, d => d.run_diff);
  const maxRunDiff = d3.max(data, d => d.run_diff);
  const yDomain = [Math.min(0, minRunDiff), Math.max(0, maxRunDiff)];
    
  const yScale = d3.scaleLinear()
    .range([height, 0])
    .domain(yDomain);

  // Adjust X-axis ticks for less clutter on mobile
  const xAxis = d3.axisBottom(xScale)
    .tickValues(xScale.domain().filter(d => isMobile ? d % 30 === 0 || d === 1 : d % 20 === 0 || d === 1 )); 
  
  // Adjusted Y-axis ticks
  const yAxis = d3.axisLeft(yScale)
    .ticks(isMobile ? 4 : 5)
    .tickPadding(5); // Added tickPadding 

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(xAxis)
    .selectAll('text')
    .attr('class', 'axis-label'); // Apply class

  svg.append('g')
    .call(yAxis) // yAxis already includes tickPadding
    .selectAll('text')
    .attr('class', 'axis-label'); // Apply class

  svg.append('line')
    .attr('x1', 0)
    .attr('x2', width)
    .attr('y1', yScale(0))
    .attr('y2', yScale(0))
    .attr('stroke', '#222')
    .attr('stroke-width', 1);

  svg.append("text") // X-axis Label
    .attr("text-anchor", "middle")
    .attr('class', 'axis-label') // Apply class
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - (isMobile ? 15 : 10)) // Adjusted bottom spacing
    .style('font-size', isMobile ? '10px' : '12px')
    .text("Game number");
  
  svg.append("text") // Y-axis Label
    .attr("text-anchor", "middle")
    .attr('class', 'axis-label') // Apply class
    .attr("transform", "rotate(-90)")
    .attr("y", -margin.left + 10) // MODIFIED: Consistent Y-axis title position
    .attr("x", -height / 2)
    .style('font-size', isMobile ? '10px' : '12px')
    .text("Run differential");

  svg.selectAll(".bar")
    .data(data)
    .enter().append("rect")
    .attr("class", "bar")
    .attr("x", d => xScale(d.gm))
    .attr("y", d => yScale(Math.max(0, d.run_diff)))
    .attr("width", xScale.bandwidth())
    .attr("height", d => Math.abs(yScale(d.run_diff) - yScale(0)))
    .attr("fill", d => d.run_diff >= 0 ? "#005a9c" : "#ef3e42");
}
fetchGameData();

document.addEventListener('DOMContentLoaded', function() {
  let groupedByYear;
  let selectedYear = null;
  let line, xScale, yScale;

  async function fetchCumulativeWinsData() {
      try {
          const response = await d3.json('https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present.json');
          // Group data by year
          groupedByYear = d3.group(response, (d) => d.year);
          populateYearSelect(Array.from(groupedByYear.keys()));
          renderCumulativeWinsChart(groupedByYear);
      } catch (error) {
          console.error('Failed to fetch data:', error);
      }
  }

  function populateYearSelect(years) {
      const yearSelect = document.getElementById('year-select');
      const currentYear = new Date().getFullYear().toString(); // Get the current year as a string
      years
          .filter(year => year !== currentYear) // Exclude the current year
          .forEach(year => {
              const option = document.createElement('option');
              option.value = year;
              option.text = year;
              yearSelect.appendChild(option);
          });

      yearSelect.addEventListener('change', function() {
          selectedYear = this.value !== "Select a season" ? this.value : null;
          updateChart();
      });
  }

  function drawLines(svg, data) {
    const currentYear = new Date().getFullYear().toString();
  
    // Create the line generator with fallback conversion for wins and gm.
    const line = d3.line()
      .x((d) => {
        const gm = Number(d.gm) || 0;
        return xScale(gm);
      })
      .y((d) => {
        const wins = Number(d.wins);
        // If wins is not a number, log an error and default to 0
        if (isNaN(wins)) {
          console.error("Invalid wins value for data point:", d);
        }
        return yScale(isNaN(wins) ? 0 : wins);
      })
      .curve(d3.curveMonotoneX);
  
    // Draw all lines except current and any selected year
    const allLinesExceptCurrentYear = Array.from(data.entries()).filter(
      (d) => d[0] !== currentYear && d[0] !== selectedYear
    );
  
    svg.selectAll('.line').remove(); // Clear previous lines
    svg.selectAll('.anno-selected-year').remove(); // Clear previous annotations
  
    svg.selectAll('.line')
      .data(allLinesExceptCurrentYear, (d) => d[0])
      .enter()
      .append('path')
      .attr('class', 'line')
      .attr('d', (d) => line(d[1]))
      .style('fill', 'none')
      .style('stroke', '#ccc')
      .style('stroke-width', 0.5);
  
    // Draw the selected year line if a year is selected
    if (selectedYear) {
      const selectedYearData = Array.from(data.entries()).filter((d) => d[0] === selectedYear);
      if (selectedYearData.length > 0) {
        selectedYearData[0][1].sort((a, b) => d3.ascending(Number(a.gm), Number(b.gm)));
        const selectedYearLastData = selectedYearData[0][1].slice(-1)[0];
  
        svg.selectAll('.line-selected-year')
          .data(selectedYearData, (d) => d[0])
          .enter()
          .append('path')
          .attr('class', 'line line-selected-year')
          .attr('d', (d) => line(d[1]))
          .style('fill', 'none')
          .style('stroke', '#ef3e42')
          .style('stroke-width', 1.5);
  
        svg.append('text')
          .attr('x', xScale(Number(selectedYearLastData.gm)) - 10)
          .attr('y', yScale(Number(selectedYearLastData.wins)) - 10)
          .text(selectedYear)
          .attr('class', 'anno-selected-year')
          .style('stroke', '#fff')
          .style('stroke-width', '4px')
          .style('stroke-linejoin', 'round')
          .attr('text-anchor', 'start')
          .style('paint-order', 'stroke')
          .clone(true)
          .style('stroke', 'none');
      }
    }
  
    // Draw the current year line
    const lineCurrentYear = Array.from(data.entries()).filter((d) => d[0] === currentYear);
    svg.selectAll('.line-current-year')
      .data(lineCurrentYear, (d) => d[0])
      .enter()
      .append('path')
      .attr('class', 'line line-current-year')
      .attr('d', (d) => line(d[1]))
      .style('fill', 'none')
      .style('stroke', '#005A9C')
      .style('stroke-width', 2);
  
    // Set lastDataCurrentYear safely
    if (lineCurrentYear.length > 0) {
      lineCurrentYear[0][1].sort((a, b) => d3.ascending(Number(a.gm), Number(b.gm)));
      const lastDataCurrentYear = lineCurrentYear[0][1].slice(-1)[0];
  
      svg.append('text')
        .attr('x', xScale(Number(lastDataCurrentYear.gm)) + 5)
        .attr('y', yScale(Number(lastDataCurrentYear.wins)) - 10)
        .text(currentYear)
        .attr('class', 'anno-dodgers')
        .style('stroke', '#fff')
        .style('stroke-width', '4px')
        .style('stroke-linejoin', 'round')
        .attr('text-anchor', 'start')
        .style('paint-order', 'stroke')
        .clone(true)
        .style('stroke', 'none');
  
      svg.append('text')
        .attr('x', xScale(Number(lastDataCurrentYear.gm)) + 5)
        .attr('y', yScale(Number(lastDataCurrentYear.wins)) + 2)
        .text(`${lastDataCurrentYear.wins} wins`)
        .attr('class', 'anno-dark')
        .style('stroke', '#fff')
        .style('stroke-width', '4px')
        .style('stroke-linejoin', 'round')
        .attr('text-anchor', 'start')
        .style('paint-order', 'stroke')
        .clone(true)
        .style('stroke', 'none');
    }
  }
  

  function updateChart() {
      const svg = d3.select('#cumulative-wins-chart svg g');
      drawLines(svg, groupedByYear);
  }

  function renderCumulativeWinsChart(data) {
      const isMobile = window.innerWidth <= 767; // Example breakpoint for mobile devices
      const margin = isMobile 
          ? { top: 20, right: 20, bottom: 60, left: 60 }  // Smaller margins for mobile
          : { top: 20, right: 10, bottom: 50, left: 60 }; // Larger margins for desktop
      const container = d3.select('#cumulative-wins-chart');
      const containerWidth = container.node().getBoundingClientRect().width;
      const width = containerWidth - margin.left - margin.right;
      const height = isMobile 
          ? Math.round(width * 1) - margin.top - margin.bottom  // Taller for mobile
          : Math.round(width * 0.5) - margin.top - margin.bottom; // 2x1 ratio for desktop

      container.selectAll('*').remove(); // Clear previous chart

      const svg = container
          .append('svg')
          .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
          .append('g')
          .attr('transform', `translate(${margin.left}, ${margin.top})`);

      xScale = d3
          .scaleLinear()
          .domain([0, 166]) // Adjust this domain as per the actual number of games
          .range([0, width]);

      yScale = d3
          .scaleLinear()
          .domain([0, d3.max(Array.from(data.values()).flat(), (d) => d.wins)])
          .range([height, 0]);

      const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('d'));
      const yAxis = d3.axisLeft(yScale).ticks(6);

      svg
          .append('g')
          .attr('transform', `translate(0, ${height})`)
          .call(xAxis);

      svg.append('g').call(yAxis);

      // X-axis Label
      svg.append("text")
          .attr("text-anchor", "middle")
          .attr('class', 'anno-dark')
          .attr("x", width / 2)
          .attr("y", height + margin.bottom - 10)
          .text("Game number in season");

      // Y-axis Label
      svg.append("text")
          .attr("text-anchor", "middle")
          .attr('class', 'anno-dark')
          .attr("transform", "rotate(-90)")
          .attr("y", -margin.left + 10) // MODIFIED: Shift Y-axis title further left
          .attr("x", -height / 2)
          .style('font-size', isMobile ? '10px' : '12px')
          .text("Cumulative wins");

      line = d3
          .line()
          .x((d) => xScale(d.gm))
          .y((d) => yScale(d.wins))
          .curve(d3.curveMonotoneX); // Smooth the line

      drawLines(svg, data);

      d3.select('#toggle-view').on('click', function() {
          updateChart();
      });
  }

  fetchCumulativeWinsData();
});








// Batting line charts: Doubles and homers
 
    document.addEventListener('DOMContentLoaded', function() {
      const chartConfigurations = [
        {
          elementId: 'cumulative-doubles-chart',
          dataField: '2b_cum',
          yAxisLabel: 'Cumulative doubles'
        },
        {
          elementId: 'cumulative-homers-chart',
          dataField: 'hr_cum',
          yAxisLabel: 'Cumulative homers'
        }
      ];
    
      async function fetchData() {
        try {
          const response = await d3.json(
            'https://stilesdata.com/dodgers/data/batting/archive/dodgers_historic_batting_gamelogs.json'
          );
          const groupedData = d3.group(response, (d) => d.year.toString());
          const maxVal = d3.max(response, d => Math.max(d['2b_cum'], d['hr_cum']));
          return { groupedData, maxVal };
        } catch (error) {
          console.error('Failed to fetch data:', error);
          return null;
        }
      }
    
      function renderChart(config, data, maxYValue) {
        const isMobile = window.innerWidth <= 767;
        const margin = isMobile 
          ? { top: 20, right: 0, bottom: 60, left: 60 } 
          : { top: 20, right: 10, bottom: 50, left: 60 };
        const container = d3.select(`#${config.elementId}`);
        const containerWidth = container.node().getBoundingClientRect().width;
        const width = containerWidth - margin.left - margin.right;
        const height = isMobile 
          ? Math.round(width * 1) - margin.top - margin.bottom
          : Math.round(width * 1.5) - margin.top - margin.bottom;
    
        const svg = container
          .append('svg')
          .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
          .append('g')
          .attr('transform', `translate(${margin.left}, ${margin.top})`);
    
        const xScale = d3
          .scaleLinear()
          .domain([0, 166])
          .range([0, width]);
    
        const yScale = d3
          .scaleLinear()
          .domain([0, maxYValue])
          .range([height, 0]);
    
        const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('d'));
        const yAxis = d3.axisLeft(yScale).ticks(6);
    
        svg
          .append('g')
          .attr('transform', `translate(0, ${height})`)
          .call(xAxis);
    
        svg.append('g').call(yAxis);
    
        svg.append("text")
          .attr("text-anchor", "middle")
          .attr('class', 'anno-dark')
          .attr("x", width / 2)
          .attr("y", height + margin.bottom - 10)
          .text("Game number in season");
    
        svg.append("text")
          .attr("text-anchor", "middle")
          .attr('class', 'anno-dark')
          .attr("transform", "rotate(-90)")
          .attr("y", -margin.left + 20)
          .attr("x", -height / 2)
          .text(config.yAxisLabel);
    
        const line = d3
          .line()
          .x((d) => xScale(d.gtm))
          .y((d) => yScale(d[config.dataField]))
          .curve(d3.curveMonotoneX);
    
        const allLinesExceptCurrentYear = Array.from(data.entries()).filter(
          (d) => d[0] !== new Date().getFullYear().toString()
        );
        svg
          .selectAll('.line')
          .data(allLinesExceptCurrentYear, (d) => d[0])
          .enter()
          .append('path')
          .attr('class', 'line')
          .attr('d', (d) => {
            return line(d[1]);
          })
          .style('fill', 'none')
          .style('stroke', '#ccc')
          .style('stroke-width', 0.5);
    
        const currentYear = new Date().getFullYear().toString();
        const lineCurrentYear = Array.from(data.entries()).filter((d) => d[0] === currentYear);
        if (lineCurrentYear.length > 0) {
          svg
            .selectAll('.line-current-year')
            .data(lineCurrentYear, (d) => d[0])
            .enter()
            .append('path')
            .attr('class', 'line')
            .attr('d', (d) => line(d[1]))
            .style('fill', 'none')
            .style('stroke', '#005A9C')
            .style('stroke-width', 2);
        }
    
        svg
          .append('text')
          .attr('x', isMobile ? xScale(60) : xScale(60))
          .attr('y', yScale(250))
          .attr('class', 'anno')
          .text(`Past: 1958-${currentYear - 1}`)
          .attr('text-anchor', 'start');
    
        const lastDataCurrentYear = data.get(currentYear)?.slice(-1)[0];
        if (lastDataCurrentYear) {
          svg
            .append('text')
            .attr('x', xScale(lastDataCurrentYear.gtm + 1))
            .attr('y', yScale(lastDataCurrentYear[config.dataField]) - 12)
            .text(currentYear)
            .attr('class', 'anno-dodgers')
            .style('stroke', '#fff')
            .style('stroke-width', '4px')
            .style('stroke-linejoin', 'round')
            .attr('text-anchor', 'start')
            .style('paint-order', 'stroke')
            .clone(true)
            .style('stroke', 'none');
    
          svg
            .append('text')
            .attr('x', xScale(lastDataCurrentYear.gtm + 1))
            .attr('y', yScale(lastDataCurrentYear[config.dataField]) + 2)
            .text(`${lastDataCurrentYear[config.dataField]} ${config.yAxisLabel.split(' ')[1].toLowerCase()}`)
            .attr('class', 'anno-dark')
            .style('stroke', '#fff')
            .style('stroke-width', '4px')
            .style('stroke-linejoin', 'round')
            .attr('text-anchor', 'start')
            .style('paint-order', 'stroke')
            .clone(true)
            .style('stroke', 'none');
        }
      }
    
      async function initializeCharts() {
        const { groupedData, maxVal } = await fetchData();
        if (groupedData) {
          chartConfigurations.forEach(config => renderChart(config, groupedData, maxVal));
        }
      }
    
      initializeCharts();
    });



    
// Pitching charts

document.addEventListener('DOMContentLoaded', function() {
  const chartConfigurations = [
    {
      elementId: 'cumulative-strikeouts-chart',
      dataField: 'so_cum',
      yAxisLabel: 'Cumulative strikeouts'
    },
    {
      elementId: 'cumulative-hits-chart',
      dataField: 'h_cum',
      yAxisLabel: 'Cumulative hits'
    }
  ];

  async function fetchData() {
    try {
      const response = await d3.json(
        'https://stilesdata.com/dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present.json'
      );
      const groupedData = d3.group(response, (d) => d.year.toString());
      const maxVal = d3.max(response, d => Math.max(d['so_cum'], d['h_cum']));
      return { groupedData, maxVal };
    } catch (error) {
      console.error('Failed to fetch data:', error);
      return null;
    }
  }

  function renderChart(config, data, maxYValue) {
    const isMobile = window.innerWidth <= 767;
    const margin = isMobile 
      ? { top: 20, right: 10, bottom: 60, left: 70 } 
      : { top: 20, right: 10, bottom: 50, left: 70 };
    const container = d3.select(`#${config.elementId}`);
    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = isMobile 
      ? Math.round(width * 1) - margin.top - margin.bottom
      : Math.round(width * 1.5) - margin.top - margin.bottom;

    const svg = container
      .append('svg')
      .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
      .append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    const xScale = d3
      .scaleLinear()
      .domain([0, 166])
      .range([0, width]);

    const yScale = d3
      .scaleLinear()
      .domain([0, maxYValue])
      .range([height, 0]);

    const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('d'));
    const yAxis = d3.axisLeft(yScale).ticks(6);

    svg
      .append('g')
      .attr('transform', `translate(0, ${height})`)
      .call(xAxis);

    svg.append('g').call(yAxis);

    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 10)
      .text("Game number in season");

    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("transform", "rotate(-90)")
      .attr("y", -margin.left + 20)
      .attr("x", -height / 2)
      .text(config.yAxisLabel);

    const line = d3
      .line()
      .x((d) => xScale(d.gtm))
      .y((d) => yScale(d[config.dataField]))
      .curve(d3.curveMonotoneX);

    const allLinesExceptCurrentYear = Array.from(data.entries()).filter(
      (d) => d[0] !== new Date().getFullYear().toString()
    );
    svg
      .selectAll('.line')
      .data(allLinesExceptCurrentYear, (d) => d[0])
      .enter()
      .append('path')
      .attr('class', 'line')
      .attr('d', (d) => line(d[1]))
      .style('fill', 'none')
      .style('stroke', '#ccc')
      .style('stroke-width', 0.5);

    const currentYear = new Date().getFullYear().toString();
    const lineCurrentYear = Array.from(data.entries()).filter((d) => d[0] === currentYear);
    if (lineCurrentYear.length > 0) {
      svg
        .selectAll('.line-current-year')
        .data(lineCurrentYear, (d) => d[0])
        .enter()
        .append('path')
        .attr('class', 'line')
        .attr('d', (d) => line(d[1]))
        .style('fill', 'none')
        .style('stroke', '#005A9C')
        .style('stroke-width', 2);
    }

    svg
      .append('text')
      .attr('x', isMobile ? xScale(70) : xScale(80))
      .attr('y', yScale(1400))
      .attr('class', 'anno')
      .text(`Past: 1958-${currentYear - 1}`)
      .attr('text-anchor', 'start');

    const lastDataCurrentYear = data.get(currentYear)?.slice(-1)[0];
    if (lastDataCurrentYear) {
      svg
        .append('text')
        .attr('x', xScale(lastDataCurrentYear.gtm + 1))
        .attr('y', yScale(lastDataCurrentYear[config.dataField]) - 12)
        .text(currentYear)
        .attr('class', 'anno-dodgers')
        .style('stroke', '#fff')
        .style('stroke-width', '4px')
        .style('stroke-linejoin', 'round')
        .attr('text-anchor', 'start')
        .style('paint-order', 'stroke')
        .clone(true)
        .style('stroke', 'none');

      svg
        .append('text')
        .attr('x', xScale(lastDataCurrentYear.gtm + 1))
        .attr('y', yScale(lastDataCurrentYear[config.dataField]) + 2)
        .text(`${lastDataCurrentYear[config.dataField]} ${config.yAxisLabel.split(' ')[1].toLowerCase()}`)
        .attr('class', 'anno-dark')
        .style('stroke', '#fff')
        .style('stroke-width', '4px')
        .style('stroke-linejoin', 'round')
        .attr('text-anchor', 'start')
        .style('paint-order', 'stroke')
        .clone(true)
        .style('stroke', 'none');
    }
  }

  async function initializeCharts() {
    const { groupedData, maxVal } = await fetchData();
    if (groupedData) {
      chartConfigurations.forEach(config => renderChart(config, groupedData, maxVal));
    }
  }

  initializeCharts();
});


// Cumulative ERA line chart

document.addEventListener('DOMContentLoaded', function() {
  async function fetchCumulativeERAData() {
    try {
      const response = await d3.json(
        'https://stilesdata.com/dodgers/data/pitching/dodgers_historic_pitching_gamelogs_1958-present.json'
      );
      // Group data by year
      const groupedByYear = d3.group(response, (d) => d.year.toString());
      renderCumulativeERAChart(groupedByYear);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  }

  function renderCumulativeERAChart(data) {
    const isMobile = window.innerWidth <= 767; // Example breakpoint for mobile devices
    const margin = isMobile 
      ? { top: 20, right: 10, bottom: 60, left: 50 }  // Smaller margins for mobile
      : { top: 20, right: 10, bottom: 50, left: 50 }; // Larger margins for desktop
    const container = d3.select('#cumulative-era-chart');
    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = isMobile 
      ? Math.round(width * 1) - margin.top - margin.bottom  // Taller for mobile
      : Math.round(width * 0.5) - margin.top - margin.bottom; // 2x1 ratio for desktop

    const svg = container
      .append('svg')
      .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
      .append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    const xScale = d3
      .scaleLinear()
      .domain([0, 166]) // Adjust this domain as per the actual number of games
      .range([0, width]);

    const yScale = d3
      .scaleLinear()
      .domain([
        0,
        d3.max(Array.from(data.values()).flat(), (d) => d.era_cum),
      ])
      .range([height, 0]);

    const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('d'));
    const yAxis = d3.axisLeft(yScale).ticks(6);

    svg
      .append('g')
      .attr('transform', `translate(0, ${height})`)
      .call(xAxis);

    svg.append('g').call(yAxis);

    // X-axis Label
    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 10)
      .text("Game number in season");

    // Y-axis Label
    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("transform", "rotate(-90)")
      .attr("y", -margin.left + 20)
      .attr("x", -height / 2)
      .text("ERA");

    const line = d3
      .line()
      .x((d) => xScale(d.gtm))
      .y((d) => yScale(d.era_cum))
      .curve(d3.curveMonotoneX); // Smooth the line

    // Draw all lines except the current year first
    const allLinesExceptCurrentYear = Array.from(data.entries()).filter(
      (d) => d[0] !== new Date().getFullYear().toString()
    );

    svg
      .selectAll('.line')
      .data(allLinesExceptCurrentYear, (d) => d[0])
      .enter()
      .append('path')
      .attr('class', 'line')
      .attr('d', (d) => line(d[1]))
      .style('fill', 'none')
      .style('stroke', '#ccc')
      .style('stroke-width', 0.5);

    const currentYear = new Date().getFullYear().toString();
    const lineCurrentYear = data.get(currentYear);

    if (lineCurrentYear) {
      svg
        .selectAll('.line-current-year')
        .data([lineCurrentYear])
        .enter()
        .append('path')
        .attr('class', 'line')
        .attr('d', line)
        .style('fill', 'none')
        .style('stroke', '#005A9C')
        .style('stroke-width', 2);

      const lastDataCurrentYear = lineCurrentYear.slice(-1)[0];

      svg
        .append('text')
        .attr('x', xScale(lastDataCurrentYear.gtm + 1))
        .attr('y', yScale(lastDataCurrentYear.era_cum) - 12)
        .text(currentYear)
        .attr('class', 'anno-dodgers')
        .style('stroke', '#fff')
        .style('stroke-width', '4px')
        .style('stroke-linejoin', 'round')
        .attr('text-anchor', 'start')
        .style('paint-order', 'stroke')
        .clone(true)
        .style('stroke', 'none');

      svg
        .append('text')
        .attr('x', xScale(lastDataCurrentYear.gtm + 1))
        .attr('y', yScale(lastDataCurrentYear.era_cum) + 2)
        .text(`${lastDataCurrentYear.era_cum} ERA`)
        .attr('class', 'anno-dark')
        .style('stroke', '#fff')
        .style('stroke-width', '4px')
        .style('stroke-linejoin', 'round')
        .attr('text-anchor', 'start')
        .style('paint-order', 'stroke')
        .clone(true)
        .style('stroke', 'none');
    }

    svg
      .append('text')
      .attr('x', isMobile ? xScale(80) : xScale(110)) // Adjusted for mobile
      .attr('y', yScale(6))
      .attr('class', 'anno')
      .text(`Past: 1958-${currentYear - 1}`)
      .attr('text-anchor', 'start');
  }

  fetchCumulativeERAData();
});




document.addEventListener('DOMContentLoaded', function () {
  const renderTable = (games, tableId) => {
    const tableBody = document.querySelector(`#${tableId} tbody`);
    tableBody.innerHTML = '';

    games.forEach(game => {
      if (game.opp_name === null) return;  // Skip games with a null opponent name

      const row = document.createElement('tr');
      if (tableId === 'last-games') {
        row.innerHTML = `
          <td>${game.date}</td>
          <td>${game.opp_name}</td>
          <td>${game.home_away === 'home' ? '<i class="fas fa-home home-icon"></i>' : '<i class="fas fa-road road-icon"></i>'}</td>
          <td class="${game.result === 'win' ? 'win' : game.result === 'loss' ? 'loss' : ''}">${game.result}</td>
        `;
      } else if (tableId === 'next-games') {
        row.innerHTML = `
          <td>${game.date}</td>
          <td>${game.opp_name}</td>
          <td>${game.home_away === 'home' ? '<i class="fas fa-home home-icon"></i>' : '<i class="fas fa-road road-icon"></i>'}</td>
          <td>${game.game_start}</td>  <!-- Display game_start time instead of result -->
        `;
      }
      tableBody.appendChild(row);
    });
  };

  const fetchDataAndRenderTables = async () => {
    try {
      const response = await fetch('https://stilesdata.com/dodgers/data/standings/dodgers_schedule.json');
      const games = await response.json();

      const lastGames = games.filter(game => game.placement === 'last');
      const nextGames = games.filter(game => game.placement === 'next');

      renderTable(lastGames, 'last-games');
      renderTable(nextGames, 'next-games');
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  fetchDataAndRenderTables();
});



document.addEventListener('DOMContentLoaded', function () {
  const url = 'https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json';

  const fetchDataAndRenderBattingTables = async () => {
      try {
          const response = await fetch(url);
          const data = await response.json();
          const limitedData = data.slice(0, 10); // Limit to the first 10 objects
          // const limitedData = data; // Limit to the first 10 objects

          renderTable(limitedData, 'table-1', ['player', 'postion', 'avg', 'obp', 'slg'], getColorScaleBlue);
          renderTable(limitedData, 'table-2', ['player', 'plateAppearances', 'bbper', 'hrper', 'soper'], getColorScale);
      } catch (error) {
          console.error('Failed to fetch data:', error);
      }
  };

  const renderTable = (data, tableId, fields, getColorScale) => {
      const tableBody = document.querySelector(`#${tableId} tbody`);
      tableBody.innerHTML = '';

      // Calculate the min and max values for each column to set the color scale
      const scales = fields.reduce((acc, field) => {
          const values = data.map(item => parseFloat(item[field]));
          acc[field] = {
              min: Math.min(...values),
              max: Math.max(...values)
          };
          return acc;
      }, {});

      data.forEach(player => {
          const row = document.createElement('tr');
          fields.forEach(field => {
              const cell = document.createElement('td');
              cell.textContent = player[field];

              // Apply conditional coloring
              if (field !== 'player' && field !== 'postion' && field !== 'plateAppearances') {
                  const value = parseFloat(player[field]);
                  const scale = scales[field];
                  cell.style.backgroundColor = getColorScale(field, value, scale.min, scale.max);
                  cell.style.color = getContrastYIQ(getColorScale(field, value, scale.min, scale.max));
              }

              row.appendChild(cell);
          });
          tableBody.appendChild(row);
      });
  };

  const getColorScale = (field, value, min, max) => {
      if (field === 'soper') {
          // Red color scale for strikeouts, reversed scale
          // return getColorFromScale(value, min, max, '#ffcccc', '#ff0000', true);
          return getColorFromScale(value, min, max, '#005a9c', '#cce5ff', false);
      } else {
          // Blue color scale for other metrics
          return getColorFromScale(value, min, max, '#cce5ff', '#005a9c', false);
      }
  };

  const getColorScaleBlue = (field, value, min, max) => {
      // Blue color scale for batting stats
      return getColorFromScale(value, min, max, '#cce5ff', '#005a9c', false);
  };

  const getColorFromScale = (value, min, max, colorMin, colorMax, reverse = false) => {
      const scale = (value - min) / (max - min);
      const ratio = reverse ? 1 - scale : scale;
      return interpolateColor(colorMin, colorMax, ratio);
  };

  const interpolateColor = (color1, color2, factor) => {
      const result = color1.slice(1).match(/.{2}/g)
          .map((hex, i) => Math.round(parseInt(hex, 16) + factor * (parseInt(color2.slice(1).match(/.{2}/g)[i], 16) - parseInt(hex, 16))))
          .map(val => val.toString(16).padStart(2, '0'))
          .join('');
      return `#${result}`;
  };

  const getContrastYIQ = (hexcolor) => {
      const r = parseInt(hexcolor.substr(1, 2), 16);
      const g = parseInt(hexcolor.substr(3, 2), 16);
      const b = parseInt(hexcolor.substr(5, 2), 16);
      const yiq = ((r*299)+(g*587)+(b*114))/1000;
      return (yiq >= 128) ? 'black' : 'white';
  };

  fetchDataAndRenderBattingTables();
});



// document.addEventListener('DOMContentLoaded', function () {
//     const url = 'https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json';

//     const fetchDataAndRenderBattingTables = async () => {
//         try {
//             const response = await fetch(url);
//             const data = await response.json();
//             const limitedData = data.slice(0, 10); // Limit to the first 10 objects

//             renderTable(limitedData, 'table-1', ['player', 'postion', 'avg', 'obp', 'slg'], getColorScaleBlue, getContrastYIQ);
//             renderTable(limitedData, 'table-2', ['player', 'plateAppearances', 'bbper', 'soper', 'hrper'], getColorScaleRedBlue, getContrastYIQ);
//         } catch (error) {
//             console.error('Failed to fetch data:', error);
//         }
//     };

//     const renderTable = (data, tableId, fields, getColorScale, getContrast) => {
//         const tableBody = document.querySelector(`#${tableId} tbody`);
//         tableBody.innerHTML = '';

//         // Calculate the min and max values for each column to set the color scale
//         const scales = fields.reduce((acc, field) => {
//             const values = data.map(item => parseFloat(item[field]));
//             acc[field] = {
//                 min: Math.min(...values),
//                 max: Math.max(...values)
//             };
//             return acc;
//         }, {});

//         data.forEach(player => {
//             const row = document.createElement('tr');
//             fields.forEach(field => {
//                 const cell = document.createElement('td');
//                 cell.textContent = player[field];

//                 // Apply conditional coloring
//                 if (field !== 'player' && field !== 'postion' && field !== 'plateAppearances') {
//                     const value = parseFloat(player[field]);
//                     const scale = scales[field];
//                     let color;

//                     // Determine which color scale to use
//                     if (field === 'soper') {
//                         color = getColorScaleRedBlue(value, scale.min, scale.max, true); // Reverse color scale for soper
//                     } else if (field === 'bbper' || field === 'hrper') {
//                         color = getColorScaleRedBlue(value, scale.min, scale.max);
//                     } else {
//                         color = getColorScaleBlue(value, scale.min, scale.max);
//                     }

//                     cell.style.backgroundColor = color;
//                     cell.style.color = getContrast(color);
//                 }

//                 cell.classList.add('table-value'); // Add the 'table-value' class for specific styles
//                 row.appendChild(cell);
//             });
//             tableBody.appendChild(row);
//         });
//     };

//     const getColorScaleBlue = (value, min, max) => {
//         const normalizedValue = (value - min) / (max - min);
//         const blueValue = Math.floor(255 - normalizedValue * 200);
//         return `rgb(0, ${blueValue}, 255)`;
//     };

//     const getColorScaleRedBlue = (value, min, max, reverse = false) => {
//         const normalizedValue = (value - min) / (max - min);
//         if (reverse) {
//             return `rgb(${255 - normalizedValue * 255}, ${100 + normalizedValue * 100}, ${100 + normalizedValue * 100})`;
//         }
//         return `rgb(${255 - normalizedValue * 255}, ${normalizedValue * 255}, ${normalizedValue * 255})`;
//     };

//     const getContrastYIQ = (hexcolor) => {
//         const r = parseInt(hexcolor.substr(1, 2), 16);
//         const g = parseInt(hexcolor.substr(3, 2), 16);
//         const b = parseInt(hexcolor.substr(5, 2), 16);
//         const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
//         return (yiq >= 128) ? 'black' : 'white';
//     };

//     fetchDataAndRenderBattingTables();
// });











document.addEventListener('DOMContentLoaded', function () {
  const renderTable = (games, tableId) => {
    const tableBody = document.querySelector(`#${tableId} tbody`);
    tableBody.innerHTML = '';

    games.forEach(game => {
      if (game.opp_name === null) return;  // Skip games with a null opponent name

      const row = document.createElement('tr');
      if (tableId === 'last-games') {
        row.innerHTML = `
          <td>${game.date}</td>
          <td>${game.opp_name}</td>
          <td>${game.home_away === 'home' ? '<i class="fas fa-home home-icon"></i>' : '<i class="fas fa-road road-icon"></i>'}</td>
          <td class="${game.result === 'win' ? 'win' : game.result === 'loss' ? 'loss' : ''}">${game.result}</td>
        `;
      } else if (tableId === 'next-games') {
        row.innerHTML = `
          <td>${game.date}</td>
          <td>${game.opp_name}</td>
          <td>${game.home_away === 'home' ? '<i class="fas fa-home home-icon"></i>' : '<i class="fas fa-road road-icon"></i>'}</td>
          <td>${game.game_start}</td>  <!-- Display game_start time instead of result -->
        `;
      }
      tableBody.appendChild(row);
    });
  };

  const fetchDataAndRenderTables = async () => {
    try {
      const response = await fetch('https://stilesdata.com/dodgers/data/standings/dodgers_schedule.json');
      const games = await response.json();

      const lastGames = games.filter(game => game.placement === 'last');
      const nextGames = games.filter(game => game.placement === 'next');

      renderTable(lastGames, 'last-games');
      renderTable(nextGames, 'next-games');
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  };

  fetchDataAndRenderTables();
});



document.addEventListener('DOMContentLoaded', function () {
  const url = 'https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json';

  const fetchDataAndRenderBattingTables = async () => {
      try {
          const response = await fetch(url);
          const data = await response.json();
          const limitedData = data.slice(0, 10); // Limit to the first 10 objects
          // const limitedData = data; // Limit to the first 10 objects

          renderTable(limitedData, 'table-1', ['player', 'postion', 'avg', 'obp', 'slg'], getColorScaleBlue);
          renderTable(limitedData, 'table-2', ['player', 'plateAppearances', 'bbper', 'hrper', 'soper'], getColorScale);
      } catch (error) {
          console.error('Failed to fetch data:', error);
      }
  };

  const renderTable = (data, tableId, fields, getColorScale) => {
      const tableBody = document.querySelector(`#${tableId} tbody`);
      tableBody.innerHTML = '';

      // Calculate the min and max values for each column to set the color scale
      const scales = fields.reduce((acc, field) => {
          const values = data.map(item => parseFloat(item[field]));
          acc[field] = {
              min: Math.min(...values),
              max: Math.max(...values)
          };
          return acc;
      }, {});

      data.forEach(player => {
          const row = document.createElement('tr');
          fields.forEach(field => {
              const cell = document.createElement('td');
              cell.textContent = player[field];

              // Apply conditional coloring
              if (field !== 'player' && field !== 'postion' && field !== 'plateAppearances') {
                  const value = parseFloat(player[field]);
                  const scale = scales[field];
                  cell.style.backgroundColor = getColorScale(field, value, scale.min, scale.max);
                  cell.style.color = getContrastYIQ(getColorScale(field, value, scale.min, scale.max));
              }

              row.appendChild(cell);
          });
          tableBody.appendChild(row);
      });
  };

  const getColorScale = (field, value, min, max) => {
      if (field === 'soper') {
          // Red color scale for strikeouts, reversed scale
          // return getColorFromScale(value, min, max, '#ffcccc', '#ff0000', true);
          return getColorFromScale(value, min, max, '#005a9c', '#cce5ff', false);
      } else {
          // Blue color scale for other metrics
          return getColorFromScale(value, min, max, '#cce5ff', '#005a9c', false);
      }
  };

  const getColorScaleBlue = (field, value, min, max) => {
      // Blue color scale for batting stats
      return getColorFromScale(value, min, max, '#cce5ff', '#005a9c', false);
  };

  const getColorFromScale = (value, min, max, colorMin, colorMax, reverse = false) => {
      const scale = (value - min) / (max - min);
      const ratio = reverse ? 1 - scale : scale;
      return interpolateColor(colorMin, colorMax, ratio);
  };

  const interpolateColor = (color1, color2, factor) => {
      const result = color1.slice(1).match(/.{2}/g)
          .map((hex, i) => Math.round(parseInt(hex, 16) + factor * (parseInt(color2.slice(1).match(/.{2}/g)[i], 16) - parseInt(hex, 16))))
          .map(val => val.toString(16).padStart(2, '0'))
          .join('');
      return `#${result}`;
  };

  const getContrastYIQ = (hexcolor) => {
      const r = parseInt(hexcolor.substr(1, 2), 16);
      const g = parseInt(hexcolor.substr(3, 2), 16);
      const b = parseInt(hexcolor.substr(5, 2), 16);
      const yiq = ((r*299)+(g*587)+(b*114))/1000;
      return (yiq >= 128) ? 'black' : 'white';
  };

  fetchDataAndRenderBattingTables();
});



// document.addEventListener('DOMContentLoaded', function () {
//     const url = 'https://stilesdata.com/dodgers/data/batting/dodgers_player_batting_current_table.json';

//     const fetchDataAndRenderBattingTables = async () => {
//         try {
//             const response = await fetch(url);
//             const data = await response.json();
//             const limitedData = data.slice(0, 10); // Limit to the first 10 objects

//             renderTable(limitedData, 'table-1', ['player', 'postion', 'avg', 'obp', 'slg'], getColorScaleBlue, getContrastYIQ);
//             renderTable(limitedData, 'table-2', ['player', 'plateAppearances', 'bbper', 'soper', 'hrper'], getColorScaleRedBlue, getContrastYIQ);
//         } catch (error) {
//             console.error('Failed to fetch data:', error);
//         }
//     };

//     const renderTable = (data, tableId, fields, getColorScale, getContrast) => {
//         const tableBody = document.querySelector(`#${tableId} tbody`);
//         tableBody.innerHTML = '';

//         // Calculate the min and max values for each column to set the color scale
//         const scales = fields.reduce((acc, field) => {
//             const values = data.map(item => parseFloat(item[field]));
//             acc[field] = {
//                 min: Math.min(...values),
//                 max: Math.max(...values)
//             };
//             return acc;
//         }, {});

//         data.forEach(player => {
//             const row = document.createElement('tr');
//             fields.forEach(field => {
//                 const cell = document.createElement('td');
//                 cell.textContent = player[field];

//                 // Apply conditional coloring
//                 if (field !== 'player' && field !== 'postion' && field !== 'plateAppearances') {
//                     const value = parseFloat(player[field]);
//                     const scale = scales[field];
//                     let color;

//                     // Determine which color scale to use
//                     if (field === 'soper') {
//                         color = getColorScaleRedBlue(value, scale.min, scale.max, true); // Reverse color scale for soper
//                     } else if (field === 'bbper' || field === 'hrper') {
//                         color = getColorScaleRedBlue(value, scale.min, scale.max);
//                     } else {
//                         color = getColorScaleBlue(value, scale.min, scale.max);
//                     }

//                     cell.style.backgroundColor = color;
//                     cell.style.color = getContrast(color);
//                 }

//                 cell.classList.add('table-value'); // Add the 'table-value' class for specific styles
//                 row.appendChild(cell);
//             });
//             tableBody.appendChild(row);
//         });
//     };

//     const getColorScaleBlue = (value, min, max) => {
//         const normalizedValue = (value - min) / (max - min);
//         const blueValue = Math.floor(255 - normalizedValue * 200);
//         return `rgb(0, ${blueValue}, 255)`;
//     };

//     const getColorScaleRedBlue = (value, min, max, reverse = false) => {
//         const normalizedValue = (value - min) / (max - min);
//         if (reverse) {
//             return `rgb(${255 - normalizedValue * 255}, ${100 + normalizedValue * 100}, ${100 + normalizedValue * 100})`;
//         }
//         return `rgb(${255 - normalizedValue * 255}, ${normalizedValue * 255}, ${normalizedValue * 255})`;
//     };

//     const getContrastYIQ = (hexcolor) => {
//         const r = parseInt(hexcolor.substr(1, 2), 16);
//         const g = parseInt(hexcolor.substr(3, 2), 16);
//         const b = parseInt(hexcolor.substr(5, 2), 16);
//         const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
//         return (yiq >= 128) ? 'black' : 'white';
//     };

//     fetchDataAndRenderBattingTables();
// });











document.addEventListener('DOMContentLoaded', function () {
  async function fetchTableData() {
    try {
      const response = await d3.json('https://stilesdata.com/dodgers/data/standings/mlb_team_attendance.json');
      renderTables(response);
      renderMaxAttendanceInfo(response);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  }

  function renderTables(data) {
    const alTable = d3.select('#al-table');
    const nlTable = d3.select('#nl-table');

    // Columns to display
    const columns = ['Team', 'Stadium', 'Fans/game']; // Always display all three columns

    // Clear any existing headers
    alTable.select('thead').remove();
    nlTable.select('thead').remove();

    // Append headers
    alTable.append('thead').append('tr')
      .selectAll('th')
      .data(columns)
      .enter().append('th')
      .text(d => d);

    nlTable.append('thead').append('tr')
      .selectAll('th')
      .data(columns)
      .enter().append('th')
      .text(d => d);

    // Filter and append rows for AL and NL teams
    const alData = data.filter(d => d.league === 'AL');
    const nlData = data.filter(d => d.league === 'NL');

    appendTableRows(alTable, alData);
    appendTableRows(nlTable, nlData);
  }

  function appendTableRows(table, data) {
    const maxAttendance = d3.max(data, d => d.attend_game);
  
    const rows = table.append('tbody').selectAll('tr')
      .data(data)
      .enter().append('tr');
  
    rows.append('td').text(d => d.team);
    rows.append('td').text(d => d.name); // Always include stadium name
  
    rows.append('td').append('div')
      .style('position', 'relative')
      .style('width', '100%')
      .each(function(d) {
        const barWidth = (d.attend_game / maxAttendance) * 100;
        const isDodgers = d.team === 'Los Angeles Dodgers';
        d3.select(this).append('div')
          .attr('class', `attendance-bar-bg ${isDodgers ? 'attendance-bar-dodgers' : ''}`)
          .style('width', `${barWidth}%`);
        d3.select(this).append('div')
          .attr('class', `attendance-bar-text ${isDodgers ? 'attendance-bar-dodgers' : ''}`)
          .text(() => {
            // Check if attend_game is a valid number; if not, use 0.
            return (d.attend_game != null && !isNaN(d.attend_game))
              ? Number(d.attend_game).toLocaleString()
              : "0";
          });
      });
  }

  function renderMaxAttendanceInfo(data) {
    const maxAttendanceTeam = data.reduce((max, team) => (team.attend_game > max.attend_game ? team : max), data[0]);
    const maxAttendanceText = `The average attendance to see the ${maxAttendanceTeam.team} at ${maxAttendanceTeam.name} so far this season is <span class='win'>${maxAttendanceTeam.attend_game.toLocaleString()}</span>, more than any other franchise in Major League Baseball.`;

    // Insert the text into a paragraph element
    d3.select('#max-attendance-info').html(maxAttendanceText);
  }

  fetchTableData();
});






// xwOBA charts
async function fetchAndRenderXwoba() {
  try {
    const data = await d3.json('https://stilesdata.com/dodgers/data/batting/dodgers_xwoba_current.json');
    
    const playerGroups = d3.group(data, d => d.player_name);
    const players = Array.from(playerGroups.keys()).sort();
    
    const allXwoba = data.map(d => d.xwoba);
    const yDomain = [
      d3.min(allXwoba) * 0.95,
      d3.max(allXwoba) * 1.05
    ];
    
    const grid = d3.select('#xwoba-grid');
    grid.html(''); 
    
    grid.style('display', 'grid')
        .style('grid-template-columns', 'repeat(auto-fit, minmax(250px, 1fr))')
        .style('gap', '15px')
        .style('width', '100%')
        .style('max-width', '1200px')
        .style('margin', '0 auto');

    // First pass: Create all containers and store them with their data
    const chartRenderQueue = [];
    players.forEach(player => {
      const playerData = playerGroups.get(player);
      const chartDiv = grid.append('div').style('width', '100%');
      chartRenderQueue.push({ chartDiv, playerData, player });
    });

    // Second pass: Measure and render after next animation frame (layout should be stable)
    requestAnimationFrame(() => {
      chartRenderQueue.forEach(({ chartDiv, playerData, player }, index) => {
        const mostRecentData = playerData.sort((a, b) => a.rn_fwd - b.rn_fwd).find(d => d.rn_fwd === 1) || playerData[0];
        
        const actualViewBoxWidth = chartDiv.node().getBoundingClientRect().width;
        const margin = {top: 20, right: 20, bottom: 30, left: 30};
        const viewBoxHeight = 150;
        const drawingWidth = actualViewBoxWidth - margin.left - margin.right;
        const drawingHeight = viewBoxHeight - margin.top - margin.bottom;
        
        const svg = chartDiv.append('svg')
          .style('width', '100%')
          .style('height', 'auto')
          .attr('viewBox', `0 0 ${actualViewBoxWidth} ${viewBoxHeight}`)
          .append('g')
          .attr('transform', `translate(${margin.left},${margin.top})`);
        
        const title = svg.append('g')
          .attr('class', 'chart-title');
        
        const playerText = title.append('text')
          .attr('x', 0)
          .attr('y', -5)
          .attr('class', 'anno-player')
          .style('font-weight', 'bold')
          .attr('text-anchor', 'start') 
          .text(player + ' ');
        
        const latestXwoba = mostRecentData.xwoba;
        const leagueAvg = mostRecentData.league_avg_xwoba;
        
        if (latestXwoba > leagueAvg) {
          playerText.append('tspan')
            .attr('class', 'trend-indicator up')
            .text('▲');
        } else if (latestXwoba < leagueAvg) {
          playerText.append('tspan')
            .attr('class', 'trend-indicator down')
            .text('▼');
        } else {
          playerText.append('tspan')
            .attr('class', 'trend-indicator neutral')
            .text('▬');
        }
        
        if (index === 0) {
          svg.append('text')
            .attr('x', 105)
            .attr('y', -5)
            .style('font-size', '11px')
            .style('fill', '#999')
            .text('▲/▼ vs. MLB avg');
        }
        
        const x = d3.scaleLinear()
          .domain([50, 1])
          .range([0, drawingWidth]);
          
        const y = d3.scaleLinear()
          .domain(yDomain)
          .range([drawingHeight, 0]);
          
        const line = d3.line()
          .x(d => x(d.rn_fwd))
          .y(d => y(d.xwoba))
          .curve(d3.curveMonotoneX);
          
        svg.append('path')
          .datum(playerData)
          .attr('fill', 'none')
          .attr('stroke', '#005A9C')
          .attr('stroke-width', 2)
          .attr('d', line);

        svg.selectAll('.dot')
          .data(playerData)
          .enter()
          .append('circle')
          .attr('class', 'dot')
          .attr('cx', d => x(d.rn_fwd))
          .attr('cy', d => y(d.xwoba))
          .attr('r', 3)
          .attr('fill', 'transparent')
          .attr('stroke', 'none')
          .append('title')
          .text(d => `xwOBA: ${d.xwoba.toFixed(3).replace(/^0\./, '.')}\nPA: ${d.rn_fwd}`);
          
        svg.append('circle')
          .attr('cx', x(1))
          .attr('cy', y(mostRecentData.xwoba))
          .attr('r', 3)
          .attr('fill', latestXwoba > leagueAvg ? '#38761d' : '#cc0000')
          .attr('stroke', '#ffffff')
          .attr('stroke-width', 1);
          
        svg.append('g')
          .attr('transform', `translate(0,${drawingHeight})`)
          .call(d3.axisBottom(x)
            .tickValues([50, 1])
            .tickFormat(d => d === 50 ? 'Oldest 50 PA' : 'Most Recent PA')
          );
          
        svg.append('g')
          .call(d3.axisLeft(y).ticks(3).tickFormat(d => d.toFixed(3).replace(/^0\./, '.')));
          
        svg.append('line')
          .attr('x1', 0)
          .attr('x2', drawingWidth)
          .attr('y1', y(leagueAvg))
          .attr('y2', y(leagueAvg))
          .attr('stroke', '#EF3E42')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '3,3');

        if (index === 0) {
          svg.append('text')
            .attr('x', drawingWidth - 10) 
            .attr('y', y(leagueAvg) + 13)
            .attr('text-anchor', 'end')
            .attr('class', 'anno')
            .attr('font-size', '8px')
            .style('fill', '#999')
            .style('stroke', 'none')
            .style('opacity', 1)
            .text(`MLB avg: ${leagueAvg.toFixed(3).replace(/^0\./, '.')}`);
        }
      });
    });
  } catch (error) {
    console.error('Error fetching xwOBA data:', error);
  }
}

document.addEventListener('DOMContentLoaded', fetchAndRenderXwoba);



// Shohei 50-50 watch charts

document.addEventListener('DOMContentLoaded', function () {
  async function fetchShoheiData() {
    const hrUrl = 'https://stilesdata.com/dodgers/data/batting/shohei_home_runs_cumulative_timeseries_combined.json';
    const sbUrl = 'https://stilesdata.com/dodgers/data/batting/shohei_stolen_bases_cumulative_timeseries_combined.json';
    const [hrData, sbData] = await Promise.all([d3.json(hrUrl), d3.json(sbUrl)]);
    return { hrData, sbData };
  }

  function renderShoheiChart(config, data) {
    const isMobile = window.innerWidth <= 767;
    const margin = isMobile
      ? { top: 20, right: 10, bottom: 60, left: 60 }
      : { top: 20, right: 10, bottom: 50, left: 60 };
    const container = d3.select(`#${config.elementId}`);
    container.selectAll('*').remove();
    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = isMobile
      ? Math.round(width * 1) - margin.top - margin.bottom
      : Math.round(width * 1.2) - margin.top - margin.bottom;

    const svg = container
      .append('svg')
      .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
      .append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Filter for 2024 and 2025
    const data2024 = data.filter(d => d.season === 2024);
    const data2025 = data.filter(d => d.season === 2025);

    const xMax = d3.max([...data2024, ...data2025], d => d.game_number);
    const yMax = d3.max([...data2024, ...data2025], d => d[config.yField]);

    const xScale = d3.scaleLinear().domain([0, xMax]).range([0, width]);
    const yScale = d3.scaleLinear().domain([0, yMax]).range([height, 0]);

    const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.format('d'));
    const yAxis = d3.axisLeft(yScale).ticks(6);

    svg.append('g')
      .attr('transform', `translate(0, ${height})`)
      .call(xAxis);

    svg.append('g').call(yAxis);

    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 10)
      .text("Game number in season");

    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("transform", "rotate(-90)")
      .attr("y", -margin.left + 20)
      .attr("x", -height / 2)
      .text(config.yAxisLabel);

    // Draw 2024 line (gray)
    const line2024 = d3.line()
      .x(d => xScale(d.game_number))
      .y(d => yScale(d[config.yField]))
      .curve(d3.curveMonotoneX);

    svg.append('path')
      .datum(data2024)
      .attr('fill', 'none')
      .attr('stroke', '#bbb')
      .attr('stroke-width', 1.5)
      .attr('d', line2024);

    // Draw 2025 line
    const line2025 = d3.line()
      .x(d => xScale(d.game_number))
      .y(d => yScale(d[config.yField]))
      .curve(d3.curveMonotoneX);

    svg.append('path')
      .datum(data2025)
      .attr('fill', 'none')
      .attr('stroke', '#005A9C')
      .attr('stroke-width', 3)
      .attr('d', line2025);

    // Add labels for 2025 (current season)
    if (data2025.length > 0) {
      const last2025 = data2025[data2025.length - 1];
      const xPosText2025 = xScale(last2025.game_number);
      const yPosLabel2025 = yScale(last2025[config.yField]) - 60; // Position label much higher
      const yPosStat2025 = yScale(last2025[config.yField]) - 46; // Position stat below label

      svg.append('text')
        .attr('x', xPosText2025)
        .attr('y', yPosLabel2025)
        .attr('class', 'anno-dodgers')
        .attr('text-anchor', 'middle') // Center text
        .style('stroke', '#fff')
        .style('stroke-width', '3px')
        .style('paint-order', 'stroke')
        .text('2025')
        .clone(true)
        .style('stroke', 'none');
      svg.append('text')
        .attr('x', xPosText2025 - 10)
        .attr('y', yPosStat2025)
        .attr('class', 'anno-dark')
        .attr('text-anchor', 'middle') // Center text
        .style('stroke', '#fff')
        .style('stroke-width', '3px')
        .style('paint-order', 'stroke')
        .text(`${last2025[config.yField]} ${config.labelText}`)
        .clone(true)
        .style('stroke', 'none');

      // Leader line for 2025
      svg.append('line')
        .attr('x1', xPosText2025)
        .attr('y1', yPosStat2025 + 6) 
        .attr('x2', xPosText2025)
        .attr('y2', yScale(last2025[config.yField])) 
        .attr('stroke', '#999999')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '3,3'); // Make dashed
    }

    // Add labels for 2024
    if (data2024.length > 0) {
      const last2024 = data2024[data2024.length - 1];
      const xPosText2024 = xScale(last2024.game_number) - 30; // Position text further left
      // Vertically center the text block with the leader line
      const midYPoint = yScale(last2024[config.yField]);
      const yPosLabel2024 = midYPoint - 7; // Position label slightly above midpoint Y
      const yPosStat2024 = midYPoint + 7;  // Position stat slightly below midpoint Y

      // Prevent labels going off-canvas
      const effectiveXPos2024 = Math.max(40, xPosText2024); 

      svg.append('text')
        .attr('x', effectiveXPos2024 -10)
        .attr('y', yPosLabel2024)
        .attr('class', 'anno')
        .attr('text-anchor', 'end')
        .style('font-weight', 'bold') 
        .style('stroke', '#fff')
        .style('stroke-width', '3px')
        .style('paint-order', 'stroke')
        .text('2024')
        .clone(true)
        .style('stroke', 'none');
      svg.append('text')
        .attr('x', effectiveXPos2024 -10)
        .attr('y', yPosStat2024)
        .attr('class', 'anno-dark')
        .attr('text-anchor', 'end') 
        .style('stroke', '#fff')
        .style('stroke-width', '3px')
        .style('paint-order', 'stroke')
        .text(`${last2024[config.yField]} ${config.labelText}`)
        .clone(true)
        .style('stroke', 'none');

      // Leader line for 2024 
      svg.append('line')
        .attr('x1', effectiveXPos2024 -3) 
        .attr('y1', midYPoint)
        .attr('x2', xScale(last2024.game_number))
        .attr('y2', midYPoint)
        .attr('stroke', '#999999')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '3,3'); // Make dashed
    }
  }

  async function initializeShoheiCharts() {
    const { hrData, sbData } = await fetchShoheiData();

    // --- Start: Dynamic Subhead Logic ---
    const data2025_hr = hrData.filter(d => d.season === 2025);
    const data2024_hr = hrData.filter(d => d.season === 2024);
    const data2024_sb = sbData.filter(d => d.season === 2024);

    if (data2025_hr.length > 0 && data2024_hr.length > 0 && data2024_sb.length > 0) {
        const lastGameEntry2025 = data2025_hr[data2025_hr.length - 1];
        const lastGameNumber2025 = lastGameEntry2025.game_number;

        // Find 2024 HR at that game number (or closest before)
        let hr2024_at_point = 0;
        const match2024_hr = data2024_hr.find(d => d.game_number === lastGameNumber2025);
        if (match2024_hr) {
            hr2024_at_point = match2024_hr.home_runs_cum;
        } else {
            const filtered_hr = data2024_hr.filter(d => d.game_number < lastGameNumber2025);
            if (filtered_hr.length > 0) {
                hr2024_at_point = filtered_hr[filtered_hr.length - 1].home_runs_cum;
            }
        }

        // Find 2024 SB at that game number (or closest before)
        let sb2024_at_point = 0;
        const match2024_sb = data2024_sb.find(d => d.game_number === lastGameNumber2025);
        if (match2024_sb) {
            sb2024_at_point = match2024_sb.sb_cum;
        } else {
            const filtered_sb = data2024_sb.filter(d => d.game_number < lastGameNumber2025);
            if (filtered_sb.length > 0) {
                sb2024_at_point = filtered_sb[filtered_sb.length - 1].sb_cum;
            }
        }

        // Construct the sentence with bold numbers
        const subheadText = `At this point in the 50-50 season in 2024, Ohtani had <strong>${hr2024_at_point}</strong> home runs and <strong>${sb2024_at_point}</strong> stolen bases.`;

        // Update the HTML
        const subheadElement = document.getElementById('shohei-comparison-subhead');
        if (subheadElement) {
            subheadElement.innerHTML = subheadText; // Use innerHTML to render the strong tags
        } else {
            console.error("Element with ID 'shohei-comparison-subhead' not found.");
        }
    }
    // --- End: Dynamic Subhead Logic ---

    renderShoheiChart(
      {
        elementId: 'shohei-homers-chart',
        yField: 'home_runs_cum',
        yAxisLabel: 'Cumulative home runs',
        labelText: 'home runs' // Use full text
      },
      hrData
    );
    renderShoheiChart(
      {
        elementId: 'shohei-sb-chart',
        yField: 'sb_cum',
        yAxisLabel: 'Cumulative stolen bases',
        labelText: 'stolen bases' // Use full text
      },
      sbData
    );
  }

  initializeShoheiCharts();
});



// New Wins Projection Chart with Confidence Interval

async function fetchWinsProjectionDataWithCI() {
  try {
    // Fetch data from the new single endpoint that includes timeseries data
    const response = await d3.json('https://stilesdata.com/dodgers/data/standings/dodgers_wins_projection_timeseries.json');

    if (!response || !response.timeseries) {
        console.error('Invalid data structure received for wins projection CI chart.');
        const container = d3.select('#wins-projection-chart-ci');
        if (!container.empty()) {
            container.html("<p class='error-message'>Could not load projection: Invalid data format.</p>");
        }
        return;
    }
    // Pass the entire response object which includes timeseries, games_played, message
    renderWinsProjectionChartWithCI(response);

  } catch (error) {
    console.error('Failed to fetch wins projection data with CI from timeseries endpoint:', error);
    const container = d3.select('#wins-projection-chart-ci');
    if (!container.empty()) {
        container.html("<p class='error-message'>Could not load wins projection data. Please check connection or try again later.</p>");
    }
  }
}

function renderWinsProjectionChartWithCI(data) {
  const { timeseries, games_played, message } = data;

  const container = d3.select('#wins-projection-chart-ci');
  if (container.empty()) {
    console.error("Container #wins-projection-chart-ci not found.");
    return;
  }
  container.html(""); // Clear previous chart or messages

  if (games_played < 10) { 
    const displayMessage = message || "A wins projection will be available after 10 games have been played.";
    console.warn("Projection info:", displayMessage);
    container.html(`<p class='info-message'>${displayMessage}</p>`);
    return;
  }
  
  if (!timeseries || timeseries.length === 0) {
    console.error("No timeseries data available for Wins Projection Chart with CI.");
    container.html("<p class='error-message'>Wins projection data is currently unavailable or empty.</p>");
    return;
  }

  const isMobile = window.innerWidth <= 767;
  const margin = isMobile 
    ? { top: 10, right: 40, bottom: 50, left: 40 } // Adjusted top and right for mobile
    : { top: 40, right: 80, bottom: 60, left: 50 }; 
  const containerWidth = container.node().getBoundingClientRect().width;
  const width = containerWidth - margin.left - margin.right;
  const height = (isMobile ? Math.round(width * 0.8) : Math.round(width * 0.5)) - margin.top - margin.bottom;

  const svg = container.append('svg')
    .attr('viewBox', `0 0 ${containerWidth} ${height + margin.top + margin.bottom}`)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const xScale = d3.scaleLinear()
    .domain([1, 162])
    .range([0, width]);

  const maxWinsInSeries = timeseries.reduce((max, p) => Math.max(max, p.upper_ci_wins, p.mean_projected_wins), 0);
  const yScale = d3.scaleLinear()
    .domain([0, d3.max([100, maxWinsInSeries])]) 
    .range([height, 0]);

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale).ticks(isMobile ? 6 : 12).tickFormat(d3.format('d')))
    .selectAll('text')
    .attr('class', 'axis-label');

  svg.append('g')
    .call(d3.axisLeft(yScale)
      .ticks(isMobile ? 4 : 5) // MODIFIED: Consistent tick count
      .tickPadding(5) // Added tickPadding
    ) // yAxis already includes tickPadding
    .selectAll('text')
    .attr('class', 'axis-label');

  const actualWinsData = timeseries.filter(d => d.game_number <= games_played);
  const lastActualGameForProjectionStart = games_played > 0 ? 
        timeseries.find(d => d.game_number === games_played) : 
        { game_number: 0, mean_projected_wins: 0, lower_ci_wins: 0, upper_ci_wins: 0 }; 
  const projectionDisplayPoints = timeseries.filter(d => d.game_number >= games_played);
  
  let meanProjectionPath = [];
  let ciAreaPath = [];

  if (games_played > 0 && lastActualGameForProjectionStart) {
      meanProjectionPath.push({ game_number: lastActualGameForProjectionStart.game_number, value: lastActualGameForProjectionStart.mean_projected_wins });
      ciAreaPath.push({ game_number: lastActualGameForProjectionStart.game_number, lower: lastActualGameForProjectionStart.mean_projected_wins, upper: lastActualGameForProjectionStart.mean_projected_wins });
  }
  
  projectionDisplayPoints.forEach(d => {
      if (d.game_number > games_played || (games_played === 0 && d.game_number >= 1)) {
          meanProjectionPath.push({ game_number: d.game_number, value: d.mean_projected_wins });
          ciAreaPath.push({ game_number: d.game_number, lower: d.lower_ci_wins, upper: d.upper_ci_wins });
      }
  });
  
  if (games_played === 0) {
        const game1Data = timeseries.find(d => d.game_number === 1);
        if (game1Data) {
            if (!meanProjectionPath.some(p => p.game_number === 1)) {
                 meanProjectionPath.unshift({ game_number: 1, value: game1Data.mean_projected_wins });
            }
            if (!ciAreaPath.some(p => p.game_number === 1)) {
                ciAreaPath.unshift({ game_number: 1, lower: game1Data.lower_ci_wins, upper: game1Data.upper_ci_wins });
            }
        }
    }

  const lineActual = d3.line()
    .x(d => xScale(d.game_number))
    .y(d => yScale(d.mean_projected_wins));

  if (actualWinsData.length > 0) {
      svg.append('path')
        .datum(actualWinsData)
        .attr('fill', 'none')
        .attr('stroke', '#005A9C')
        .attr('stroke-width', 2.5)
        .attr('d', lineActual);
  }
    
  const areaGenerator = d3.area()
    .x(d => xScale(d.game_number))
    .y0(d => yScale(d.lower))
    .y1(d => yScale(d.upper));

  if (ciAreaPath.length > 1) {
      svg.append('path')
        .datum(ciAreaPath)
        .attr('fill', '#005a9c')
        .attr('opacity', 0.1)
        .attr('d', areaGenerator);
  }
    
  const projectionLine = d3.line()
    .x(d => xScale(d.game_number))
    .y(d => yScale(d.value));

  if (meanProjectionPath.length > 1) {
      svg.append('path')
        .datum(meanProjectionPath)
        .attr('fill', 'none')
        .attr('stroke', '#4A4A4A') 
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '5,5')
        .attr('d', projectionLine);
  }

  const finalProjectionPoint = timeseries.find(d => d.game_number === 162);
  if (finalProjectionPoint && games_played >= 10) {
      const finalMeanWins = finalProjectionPoint.mean_projected_wins;
      const ciUpper = finalProjectionPoint.upper_ci_wins;
      const ciLower = finalProjectionPoint.lower_ci_wins;

      // Projected Mean Wins Annotation
      svg.append('text')
        .attr('x', isMobile ? xScale(162) - 5 : xScale(162) + 5)
        .attr('y', yScale(finalMeanWins))
        .attr('text-anchor', isMobile ? 'end' : 'start')
        .attr('class', 'anno-dark-small')
        .style('font-size', isMobile ? '9px' : '11px') // Adjusted font size for mobile
        .text(isMobile ? `${finalMeanWins.toFixed(0)} wins` : `Proj: ${finalMeanWins.toFixed(0)} wins`);

      // CI Upper Annotation
      svg.append('text')
        .attr('x', isMobile ? xScale(162) - 5 : xScale(162) + 5)
        .attr('y', yScale(ciUpper) + (isMobile ? -2 : (yScale(finalMeanWins) > yScale(ciUpper) ? 5 : -3)))
        .attr('text-anchor', isMobile ? 'end' : 'start')
        .attr('class', 'anno-grey-small')
        .style('font-size', isMobile ? '8px' : '10px') // Adjusted font size for mobile
        .text(`${Math.round(ciUpper)}`);

      // CI Lower Annotation
      svg.append('text')
        .attr('x', isMobile ? xScale(162) - 5 : xScale(162) + 5)
        .attr('y', yScale(ciLower) + (isMobile ? 6 : (yScale(finalMeanWins) < yScale(ciLower) ? -5 : 3)))
        .attr('text-anchor', isMobile ? 'end' : 'start')
        .attr('class', 'anno-grey-small')
        .style('font-size', isMobile ? '8px' : '10px') // Adjusted font size for mobile
        .text(`${Math.round(ciLower)}`);
        
      // Vertical CI Line
      if (Math.abs(yScale(ciUpper) - yScale(ciLower)) > (isMobile ? 8 : 10)) { // Adjust min difference for mobile
        svg.append('line')
            .attr('x1', isMobile ? xScale(162) - 2.5 : xScale(162) + 2.5)
            .attr('x2', isMobile ? xScale(162) - 2.5 : xScale(162) + 2.5)
            .attr('y1', yScale(ciUpper))
            .attr('y2', yScale(ciLower))
            .attr('stroke', '#A5ACAF')
            .attr('stroke-width', 1);
      }
  }

  svg.append('text') // X-axis Label
    .attr('text-anchor', 'middle')
    .attr('class', 'axis-label')
    .attr('x', width / 2)
    .attr('y', height + margin.bottom - (isMobile ? 10 : 15))
    .style('font-size', isMobile ? '10px' : '12px')
    .text('Game number');

  svg.append('text') // Y-axis Label
    .attr('text-anchor', 'middle')
    .attr('class', 'axis-label')
    .attr('transform', 'rotate(-90)')
    .attr('y', -margin.left + 10) 
    .attr('x', -height / 2)
    .style('font-size', isMobile ? '10px' : '12px')
    .text('Cumulative wins');

        
  // const legendData = [
  //     { label: "Actual Wins", color: "#005A9C", type: "line" },
  //     { label: "Mean Projection", color: "#4A4A4A", type: "dashed-line" },
  //     { label: "95% confidence interval", color: "#005a9c", type: "area" }
  // ];
  //
  // const legend = svg.append("g")
  //     .attr("class", "legend")
  //     .attr("transform", `translate(${isMobile ? 10 : 0}, ${isMobile ? -margin.top + 12 : -margin.top + 12})`);
  //
  // const legendItemWidth = isMobile ? 75 : 110;
  // const legendItem = legend.selectAll(".legend-item")
  //     .data(legendData)
  //     .enter().append("g")
  //     .attr("class", "legend-item")
  //     .attr("transform", (d, i) => `translate(${i * legendItemWidth}, 0)`);
  //
  // legendItem.append("rect")
  //     .attr("x", 0)
  //     .attr("y", -7)
  //     .attr("width", d => d.type === "area" ? 15 : 20)
  //     .attr("height", d => d.type === "area" ? 10 : 2 )
  //     .style("fill", d => d.color)
  //     .style("stroke", d => d.type === "dashed-line" ? d.color : "none")
  //     .style("stroke-width", d => d.type === "dashed-line" ? 2 : 0)
  //     .style("stroke-dasharray", d => d.type === "dashed-line" ? "3,3" : "none")
  //     .attr("opacity", d => d.type === "area" ? 0.3 : 1);
  //
  // legendItem.append("text")
  //     .attr("x", d => d.type === "area" ? 20 : 25)
  //     .attr("y", 0)
  //     .attr("dy", "0.0em")
  //     .attr("class","legend-text")
  //     .style("text-anchor", "start")
  //     .style("font-size", isMobile? "9px" : "11px")
  //     .text(d => d.label);
}

async function initWinsProjectionChartWithCI() {
  const container = d3.select('#wins-projection-chart-ci');
  if (!container.empty()) {
    // Clear any existing content (like old charts or error messages) before fetching
    container.html(''); 
    await fetchWinsProjectionDataWithCI();
  } else {
    console.log("Wins projection CI chart container (#wins-projection-chart-ci) not found on this page, skipping initialization.");
  }
}

// Ensure this is the primary initialization for the CI chart
// Remove or comment out other initializations for #wins-projection-chart-ci if they exist.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWinsProjectionChartWithCI);
} else {
  initWinsProjectionChartWithCI(); // Call if DOM is already loaded
}