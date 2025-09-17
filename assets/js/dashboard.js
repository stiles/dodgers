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
    .attr('x', isMobile ? xScale(10) : xScale(10))
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
      .attr('y', yScale(lastDataCurrent.gb) - 12)
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
              return `Games up: ${gb}`;
          } else if (gb < 0) {
              return `Games back: ${Math.abs(gb)}`;
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
        .attr('y', yScale(Number(lastDataCurrentYear.wins)) - 12)
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
          const legend = svg.append('text')
            .attr('x', 125)
            .attr('y', -5)
            .style('font-size', '12px')
            .style('fill', '#999');
          legend.append('tspan').text('');
          legend.append('tspan').text('▲').style('fill', '#38761d');
          legend.append('tspan').text(' / ').style('fill', '#999');
          legend.append('tspan').text('▼').style('fill', '#cc0000');
          legend.append('tspan').text(' vs. MLB avg').style('fill', '#999');
        }
        
        const x = d3.scaleLinear()
          .domain([100, 1])
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
            .tickValues([100, 1])
            .tickFormat(d => d === 100 ? 'Oldest 100' : 'Most Recent PA')
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
          const mlbAvgYOffset = latestXwoba >= leagueAvg ? -5 : 13; // prefer above the line when applicable
          const mlbAvg = `MLB avg: ${leagueAvg.toFixed(3).replace(/^0\./, '.')}`;
          const label = svg.append('text')
            .attr('x', drawingWidth - 10)
            .attr('y', y(leagueAvg) + mlbAvgYOffset)
            .attr('text-anchor', 'end')
            .attr('class', 'anno')
            .attr('font-size', '10px')
            .style('fill', '#b1b1b1')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('stroke-linejoin', 'round')
            .style('paint-order', 'stroke')
            .text(mlbAvg)
            .clone(true)
            .style('stroke', 'none');
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

    // Track 2025 label position for basic collision checks with 2024
    const label2025 = { x: null, yLabel: null, yStat: null };

    // Add labels for 2025 (current season)
    if (data2025.length > 0) {
      const last2025 = data2025[data2025.length - 1];
      const xPosText2025 = xScale(last2025.game_number);
      // On desktop, lift the 2025 label slightly higher to avoid collisions with 2024
      let yPosLabel2025 = yScale(last2025[config.yField]) - (isMobile ? 44 : 64);
      let yPosStat2025 = yScale(last2025[config.yField]) - (isMobile ? 30 : 50);
      // Clamp to keep inside chart area
      yPosLabel2025 = Math.max(12, yPosLabel2025);
      yPosStat2025 = Math.max(26, yPosStat2025);

      // Save for later overlap checks
      label2025.x = xPosText2025;
      label2025.yLabel = yPosLabel2025;
      label2025.yStat = yPosStat2025;

      svg.append('text')
        .attr('x', xPosText2025)
        .attr('y', yPosLabel2025)
        .attr('class', 'anno-dodgers')
        .attr('text-anchor', 'middle') // Center text
        .style('stroke', '#fff')
        .style('stroke-width', '3px')
        .style('stroke-linejoin', 'round')
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
        .style('stroke-linejoin', 'round')
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
      const xPoint2024 = xScale(last2024.game_number);
      const yPoint2024 = yScale(last2024[config.yField]);

      // Simple collision heuristic with 2025 label area
      // Loosen thresholds to capture more near-overlap scenarios on desktop
      const nearX2025 = label2025.x !== null && Math.abs(xPoint2024 - label2025.x) < (isMobile ? 42 : 60);
      const nearY2025 = label2025.yStat !== null && Math.abs(yPoint2024 - label2025.yStat) < (isMobile ? 28 : 36);
      const overlaps2025 = nearX2025 && nearY2025;

      if (isMobile || overlaps2025 || (config.elementId === 'shohei-homers-chart' && !isMobile)) {
        const isHR = config.elementId === 'shohei-homers-chart';
        const isSB = config.elementId === 'shohei-sb-chart';

        if (isHR) {
          // 6 o'clock: vertical leader downward, centered text below
          const yOffset = overlaps2025 ? 42 : 36;
          let yTarget = Math.min(height - 12, yPoint2024 + yOffset);
          // Nudge further down if close to 2025 stat
          if (label2025.yStat !== null && Math.abs(yTarget - label2025.yStat) < 26) {
            yTarget = Math.min(height - 12, label2025.yStat + 30);
          }

          svg.append('text')
            .attr('x', xPoint2024)
            .attr('y', yTarget + 10)
            .attr('class', 'anno')
            .attr('text-anchor', 'end')
            .style('font-weight', 'bold')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('stroke-linejoin', 'round')
            .style('paint-order', 'stroke')
            .text('2024')
            .clone(true)
            .style('stroke', 'none');

          svg.append('text')
            .attr('x', xPoint2024)
            .attr('y', yTarget + 20)
            .attr('class', 'anno-dark')
            .attr('text-anchor', 'end')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('stroke-linejoin', 'round')
            .style('paint-order', 'stroke')
            .text(`${last2024[config.yField]} ${config.labelText}`)
            .clone(true)
            .style('stroke', 'none');

          svg.append('line')
            .attr('x1', xPoint2024)
            .attr('y1', yPoint2024)
            .attr('x2', xPoint2024)
            .attr('y2', yTarget - 6)
            .attr('stroke', '#999999')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '3,3');
        } else if (isSB) {
          // 9 o'clock: horizontal leader left, text aligned to the left of the point
          const xEdgePadding = 10;
          const xOffset = overlaps2025 ? 40 : 34;
          const xTarget = Math.max(xEdgePadding, xPoint2024 - xOffset);
          const yTarget = Math.min(height - 12, Math.max(12, yPoint2024));

          svg.append('text')
            .attr('x', xTarget)
            .attr('y', yTarget - 12)
            .attr('class', 'anno')
            .attr('text-anchor', 'end')
            .style('font-weight', 'bold')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('stroke-linejoin', 'round')
            .style('paint-order', 'stroke')
            .text('2024')
            .clone(true)
            .style('stroke', 'none');

          svg.append('text')
            .attr('x', xTarget)
            .attr('y', yTarget + 3)
            .attr('class', 'anno-dark')
            .attr('text-anchor', 'end')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('stroke-linejoin', 'round')
            .style('paint-order', 'stroke')
            .text(`${last2024[config.yField]} ${config.labelText}`)
            .clone(true)
            .style('stroke', 'none');

          svg.append('line')
            .attr('x1', xTarget + 6)
            .attr('y1', yPoint2024)
            .attr('x2', xPoint2024)
            .attr('y2', yPoint2024)
            .attr('stroke', '#999999')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '3,3');
        } else {
          // Fallback: diagonal placement similar to previous behavior
          const xEdgePadding = 10;
          const xOffset = 18;
          const yOffset = 28;
          const placeRight = xPoint2024 <= width * 0.7;
          const xTarget = Math.max(
            xEdgePadding,
            Math.min(width - xEdgePadding, xPoint2024 + (placeRight ? xOffset : -xOffset))
          );
          const yTarget = Math.min(height - 12, yPoint2024 + yOffset);

          svg.append('text')
            .attr('x', xTarget)
            .attr('y', yTarget - 12)
            .attr('class', 'anno')
            .attr('text-anchor', placeRight ? 'start' : 'end')
            .style('font-weight', 'bold')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('paint-order', 'stroke')
            .text('2024')
            .clone(true)
            .style('stroke', 'none');

          svg.append('text')
            .attr('x', xTarget)
            .attr('y', yTarget)
            .attr('class', 'anno-dark')
            .attr('text-anchor', placeRight ? 'start' : 'end')
            .style('stroke', '#fff')
            .style('stroke-width', '3px')
            .style('paint-order', 'stroke')
            .text(`${last2024[config.yField]} ${config.labelText}`)
            .clone(true)
            .style('stroke', 'none');

          svg.append('line')
            .attr('x1', xPoint2024)
            .attr('y1', yPoint2024)
            .attr('x2', xTarget)
            .attr('y2', yTarget - 14)
            .attr('stroke', '#999999')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '3,3');
        }
      } else {
        // Desktop: keep label to the left, centered vertically on the point
        const xPosText2024 = xPoint2024 - 30; // Position text further left
        const midYPoint = yPoint2024;
        const yPosLabel2024 = midYPoint - 7;
        const yPosStat2024 = midYPoint + 7;
        const effectiveXPos2024 = Math.max(40, xPosText2024);

        svg.append('text')
          .attr('x', effectiveXPos2024 - 10)
          .attr('y', yPosLabel2024)
          .attr('class', 'anno')
          .attr('text-anchor', 'end')
          .style('font-weight', 'bold')
          .style('stroke', '#fff')
          .style('stroke-width', '3px')
          .style('stroke-linejoin', 'round')
          .style('paint-order', 'stroke')
          .text('2024')
          .clone(true)
          .style('stroke', 'none');

        svg.append('text')
          .attr('x', effectiveXPos2024 - 10)
          .attr('y', yPosStat2024)
          .attr('class', 'anno-dark')
          .attr('text-anchor', 'end')
          .style('stroke', '#fff')
          .style('stroke-width', '3px')
          .style('stroke-linejoin', 'round')
          .style('paint-order', 'stroke')
          .text(`${last2024[config.yField]} ${config.labelText}`)
          .clone(true)
          .style('stroke', 'none');

        svg.append('line')
          .attr('x1', effectiveXPos2024 - 3)
          .attr('y1', midYPoint)
          .attr('x2', xPoint2024)
          .attr('y2', midYPoint)
          .attr('stroke', '#999999')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '3,3');
      }
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
        labelText: 'homers' // Use full text
      },
      hrData
    );
    renderShoheiChart(
      {
        elementId: 'shohei-sb-chart',
        yField: 'sb_cum',
        yAxisLabel: 'Cumulative stolen bases',
        labelText: 'stolen' // Use full text
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
        .attr('x', isMobile ? xScale(162) - 5 : xScale(162) - 95)
        .attr('y', isMobile ? yScale(finalMeanWins) : yScale(finalMeanWins) - 5)
        .attr('text-anchor', isMobile ? 'end' : 'start')
        .attr('class', 'anno-dark-small')
        .style('font-size', isMobile ? '9px' : '11px') // Adjusted font size for mobile
        .text(isMobile ? `${finalMeanWins.toFixed(0)} wins` : `Projected: ${finalMeanWins.toFixed(0)} wins`);

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


// Adjust "Games up/back" stat card labeling and color based on division rank
(function () {
  function updateGamesUpBackCard() {
    const cards = document.querySelectorAll('.stat-card');
    cards.forEach(card => {
      const labelEl = card.querySelector('.stat-card-label');
      const valueEl = card.querySelector('.stat-card-value');
      const contextEl = card.querySelector('.stat-card-context');
      if (!labelEl || !valueEl || !contextEl) return;
      const labelText = labelEl.textContent.trim().toLowerCase();
      if (labelText !== 'games up/back') return;

      const contextText = contextEl.textContent || '';
      const inFirst = /\b1st\b/i.test(contextText);
      // Update label based on rank
      labelEl.textContent = inFirst ? 'Games up' : 'Game back';
      // Only color the number when not in first
      valueEl.classList.remove('loss');
      valueEl.style.color = inFirst ? '' : '#ef3e42';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateGamesUpBackCard);
  } else {
    updateGamesUpBackCard();
  }
})();


// Umpire Scorecard
(function () {
  async function fetchUmpireData() {
    try {
      const response = await d3.json('https://stilesdata.com/dodgers/data/summary/umpire_summary.json');
      renderUmpireScorecard(response);
      } catch (error) {
      console.error('Failed to fetch umpire scorecard data:', error);
    }
  }

  function renderUmpireScorecard(data) {
    // Left column: bars
    const chartDiv = d3.select('#umpire-scorecard-chart');
    chartDiv.html('');

    // Season Chart
    const seasonData = data.season_summary;

    const seasonActualStrikes = seasonData.total_called_strikes - seasonData.bad_calls_count;
    const seasonBadCalls = seasonData.bad_calls_count;

    console.log(seasonActualStrikes);
    console.log(seasonBadCalls);

    if (seasonData && seasonData.correct_strikes_pct !== undefined && seasonData.incorrect_strikes_pct !== undefined) {
      const seasonBarWrapper = chartDiv.append('div').attr('class', 'chart-bar-wrapper');
      const seasonLabelLine = seasonBarWrapper.append('div').attr('class', 'chart-label-line');
      seasonLabelLine.append('div').attr('class', 'chart-label').text('This season');
      // Show raw totals above the bar
      seasonLabelLine.append('div').attr('class', 'chart-percentages').html(
        `<span class="good-calls-label">${seasonActualStrikes.toLocaleString()} </span> good calls / <span class="bad-calls-label">${seasonBadCalls} </span> bad calls`
      );
      const seasonBarInner = seasonBarWrapper.append('div').attr('class', 'chart-bar');
      
      // Add segments with proper widths
      const correctPct = seasonData.correct_strikes_pct;
      const incorrectPct = seasonData.incorrect_strikes_pct;
      
      if (correctPct > 0) {
        seasonBarInner.append('div')
          .attr('class', 'chart-segment strikes')
          .style('width', `${correctPct}%`)
          // Show percentage inside the bar if wide enough
          .text(correctPct >= 15 ? `${correctPct.toFixed(0)}%` : '');
      }
      
      if (incorrectPct > 0) {
        seasonBarInner.append('div')
          .attr('class', 'chart-segment balls')
          .style('width', `${incorrectPct}%`)
          // Show percentage inside the bar if wide enough
          .text(incorrectPct >= 15 ? `${incorrectPct.toFixed(0)}%` : '');
      }
    }

    // Last Game Chart
    const gameData = data.last_game_summary;

    const gameActualStrikes = gameData.total_called_strikes - gameData.bad_calls_count;
    const gameBadCalls = gameData.bad_calls_count;

    if (gameData && gameData.correct_strikes_pct !== undefined && gameData.incorrect_strikes_pct !== undefined) {
      const gameBarWrapper = chartDiv.append('div').attr('class', 'chart-bar-wrapper');
      const gameLabelLine = gameBarWrapper.append('div').attr('class', 'chart-label-line');
      // Format the date as 'Month Day, Year'
      let lastGameLabel = 'Last game';
      if (gameData.date) {
        lastGameLabel += `: ${gameData.date}`;
      }
      gameLabelLine.append('div').attr('class', 'chart-label').text(lastGameLabel);
      // Show raw totals above the bar
      gameLabelLine.append('div').attr('class', 'chart-percentages').html(
        `<span class="good-calls-label">${gameActualStrikes} </span> / <span class="bad-calls-label">${gameBadCalls} </span>`
      );
      const gameBarInner = gameBarWrapper.append('div').attr('class', 'chart-bar');
      
      // Add segments with proper widths
      const correctPct = gameData.correct_strikes_pct;
      const incorrectPct = gameData.incorrect_strikes_pct;
      
      if (correctPct > 0) {
        gameBarInner.append('div')
          .attr('class', 'chart-segment strikes')
          // Show percentage inside the bar if wide enough
          .style('width', `${correctPct}%`)
          .text(correctPct >= 15 ? `${correctPct.toFixed(0)}%` : ''); 
      }
      
      if (incorrectPct > 0) {
        gameBarInner.append('div')
          .attr('class', 'chart-segment balls')
          // Show percentage inside the bar if wide enough
          .style('width', `${incorrectPct}%`)
          .text(incorrectPct >= 15 ? `${incorrectPct.toFixed(0)}%` : ''); 
      }

      // Home plate umpire caption (matches italics style used in worst calls pitch type)
      if (gameData.home_plate_umpire) {
        chartDiv
          .append('div')
          .attr('class', 'call-details')
          .html(`<em>Home plate umpire: ${gameData.home_plate_umpire}</em>`);
      }
    }

    // Right column: worst calls
    const worstCallsDiv = d3.select('#umpire-worst-calls');
    worstCallsDiv.html('');
    const worstCallsList = worstCallsDiv.append('ul').attr('class', 'worst-calls-list');
    
    if (data.worst_calls_of_season && data.worst_calls_of_season.length > 0) {
      data.worst_calls_of_season.slice(0, 4).forEach(call => { // Limit to top 5 worst calls
        const listItem = worstCallsList.append('li');
        listItem.html(`
          <div class="call-date">
            ${call.date_formatted || call.date}
          </div>
          <div class="call-headline">
          ${call.batter} vs. ${call.pitcher}
            <a href="${call.video_link}" target="_blank" class="video-link" aria-label="Watch video replay">
              <svg width="32" height="32" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Outer red circle with white fill -->
            <circle cx="32" cy="32" r="30" fill="#ffffff" stroke="#ef3e42" stroke-width="4"/>
            
            <!-- Inner soft circle for subtle elevation -->
            <circle cx="32" cy="32" r="28" fill="#fefefe" filter="url(#shadow)" />

            <!-- Play icon in the center -->
            <path d="M26 20L44 32L26 44V20Z" fill="#ef3e42"/>

            <!-- Drop shadow definition -->
            <defs>
              <filter id="shadow" x="0" y="0" width="64" height="64" filterUnits="userSpaceOnUse">
                <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000000" flood-opacity="0.1"/>
              </filter>
            </defs>
          </svg>
            </a>
          </div>
          <div class="call-details">
             <b>${call.distance_inches.toFixed(2)}"</b> from zone &bull; <b>${call.velocity_mph.toFixed(0)}</b> mph &bull; <em>${call.pitch_type}</em>
          </div>
          
        `);
      });
      } else {
      worstCallsList.append('li').html('<div class="call-details" style="font-style: italic; color: #999;">No incorrect calls data available.</div>');
    }
  }

  if (document.getElementById('umpire-scorecard-chart')) {
    fetchUmpireData();
  }
})();

// Umpire Scorecard - Pitching (balls called in-zone)
(function () {
  async function fetchUmpireDataPitching() {
    try {
      const response = await d3.json('https://stilesdata.com/dodgers/data/summary/umpire_summary.json');
      renderUmpireScorecardPitching(response);
    } catch (error) {
      console.error('Failed to fetch umpire scorecard pitching data:', error);
    }
  }

  function renderUmpireScorecardPitching(data) {
    const chartDiv = d3.select('#umpire-scorecard-pitching-chart');
    if (chartDiv.empty()) return;
    chartDiv.html('');

    const pitchingSeason = data.pitching_season_summary;
    const pitchingLast = data.pitching_last_game_summary;

    if (pitchingSeason) {
      const seasonBarWrapper = chartDiv.append('div').attr('class', 'chart-bar-wrapper');
      const seasonLabelLine = seasonBarWrapper.append('div').attr('class', 'chart-label-line');
      seasonLabelLine.append('div').attr('class', 'chart-label').text('This season');
      const totalBallsSeason = pitchingSeason.total_called_balls || 0;
      const badBallsSeason = pitchingSeason.bad_calls_count || 0;
      const goodBallsSeason = Math.max(0, totalBallsSeason - badBallsSeason);
      seasonLabelLine.append('div').attr('class', 'chart-percentages').html(
        `<span class="good-calls-label">${goodBallsSeason.toLocaleString()} </span> good calls / <span class="bad-calls-label">${badBallsSeason.toLocaleString()} </span> bad calls`
      );

      const seasonBarInner = seasonBarWrapper.append('div').attr('class', 'chart-bar');
      const correctPct = pitchingSeason.correct_balls_pct || 0;
      const incorrectPct = pitchingSeason.incorrect_balls_pct || 0;
      if (correctPct > 0) {
        seasonBarInner.append('div')
          .attr('class', 'chart-segment strikes')
          .style('width', `${correctPct}%`)
          .text(correctPct >= 15 ? `${correctPct.toFixed(0)}%` : '');
      }
      if (incorrectPct > 0) {
        seasonBarInner.append('div')
          .attr('class', 'chart-segment balls')
          .style('width', `${incorrectPct}%`)
          .text(incorrectPct >= 15 ? `${incorrectPct.toFixed(0)}%` : '');
      }
    }

    if (pitchingLast) {
      const gameBarWrapper = chartDiv.append('div').attr('class', 'chart-bar-wrapper');
      const gameLabelLine = gameBarWrapper.append('div').attr('class', 'chart-label-line');
      gameLabelLine.append('div').attr('class', 'chart-label').text(`Last game: ${pitchingLast.date}`);
      const totalBallsGame = pitchingLast.total_called_balls || 0;
      const badBallsGame = pitchingLast.bad_calls_count || 0;
      const goodBallsGame = Math.max(0, totalBallsGame - badBallsGame);
      gameLabelLine.append('div').attr('class', 'chart-percentages').html(
        `<span class="good-calls-label">${goodBallsGame.toLocaleString()} </span> / <span class="bad-calls-label">${badBallsGame.toLocaleString()} </span>`
      );

      const gameBarInner = gameBarWrapper.append('div').attr('class', 'chart-bar');
      const correctPct = pitchingLast.correct_balls_pct || 0;
      const incorrectPct = pitchingLast.incorrect_balls_pct || 0;
      if (correctPct > 0) {
        gameBarInner.append('div')
          .attr('class', 'chart-segment strikes')
          .style('width', `${correctPct}%`)
          .text(correctPct >= 15 ? `${correctPct.toFixed(0)}%` : '');
      }
      if (incorrectPct > 0) {
        gameBarInner.append('div')
          .attr('class', 'chart-segment balls')
          .style('width', `${incorrectPct}%`)
          .text(incorrectPct >= 15 ? `${incorrectPct.toFixed(0)}%` : '');
      }

      // Home plate umpire caption (reuse batting field; same game, same umpire)
      if (data.last_game_summary && data.last_game_summary.home_plate_umpire) {
        chartDiv
          .append('div')
          .attr('class', 'call-details')
          .html(`<em>Home plate umpire: ${data.last_game_summary.home_plate_umpire}</em>`);
      }
    }

    // Worst calls list
    const worstCallsDiv = d3.select('#umpire-worst-calls-pitching');
    if (worstCallsDiv.empty()) return;
    worstCallsDiv.html('');
    const list = worstCallsDiv.append('ul').attr('class', 'worst-calls-list');
    const worst = data.pitching_worst_calls_of_season || [];
    if (worst.length > 0) {
      worst.slice(0, 4).forEach(call => {
        const item = list.append('li');
        item.html(`
          <div class="call-date">${call.date_formatted || call.date}</div>
          <div class="call-headline">
            ${call.batter} vs. ${call.pitcher}
            <a href="${call.video_link}" target="_blank" class="video-link" aria-label="Watch video replay">
              <svg width="32" height="32" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="32" cy="32" r="30" fill="#ffffff" stroke="#ef3e42" stroke-width="4"/>
                <circle cx="32" cy="32" r="28" fill="#fefefe" />
                <path d="M26 20L44 32L26 44V20Z" fill="#ef3e42"/>
              </svg>
            </a>
          </div>
          <div class="call-details">
             <b>${(call.distance_inches || 0).toFixed(2)}"</b> inside zone • <b>${(call.velocity_mph || 0).toFixed(0)}</b> mph • <em>${call.pitch_type || ''}</em>
          </div>
        `);
      });
    } else {
      list.append('li').html('<div class="call-details" style="font-style: italic; color: #999;">No incorrect ball calls data available.</div>');
    }
  }

  if (document.getElementById('umpire-scorecard-pitching-chart')) {
    fetchUmpireDataPitching();
  }
})();

// Shohei Ohtani Pitching Visualization
document.addEventListener('DOMContentLoaded', function () {
  if (!document.getElementById('shohei-pitching-container')) {
    return;
  }

  async function fetchOhtaniPitchData() {
    try {
      const cacheBuster = `?v=${Date.now()}`;
      const mixResponse = await d3.json(`https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitch_mix.json${cacheBuster}`);
      const pitchesResponse = await d3.json(`https://stilesdata.com/dodgers/data/pitching/shohei_ohtani_pitches.json${cacheBuster}`);
      
      // Calculate total pitches and games
      const totalPitches = pitchesResponse.length;
      const uniqueGames = new Set(pitchesResponse.map(d => d.gd)).size;
      
      // Update the description with actual counts
      const descriptionElement = document.querySelector('#shohei-pitching-container').previousElementSibling;
      if (descriptionElement && descriptionElement.classList.contains('chart-chatter')) {
        descriptionElement.textContent = `A detailed look at Ohtani's ${totalPitches} pitches over ${uniqueGames} games this season, showing his pitch mix, average velocity and locations.`;
      }
      
      // Calculate average velocity for pitch mix data
      const pitchesData = d3.group(pitchesResponse, d => d.pitch_type_abbr);
      mixResponse.forEach(mix => {
        const pitchesForType = pitchesData.get(mix.pitchType);
        if (pitchesForType) {
          mix.avg_vel = d3.mean(pitchesForType, d => d.vel);
      } else {
          mix.avg_vel = 0;
        }
      });
      
      renderOhtaniPitchMix(mixResponse);
      renderOhtaniPitchLocation(pitchesResponse);
    } catch (error) {
      console.error('Failed to fetch Ohtani pitch data:', error);
    }
  }

  const pitchColor = d3.scaleOrdinal()
    .domain(['FF', 'ST', 'SI', 'FS', 'FC', 'CU', 'CS'])
    .range(['#1b9e77','#d95f02','#7570b3','#e7298a','#66a61e','#e6ab02']); // xgfs_fancy6 palette

  function renderOhtaniPitchMix(data) {
    const container = d3.select('#shohei-pitch-mix-chart');
    container.html('<h3 class="visual-subhead">Pitch Mix</h3>');
    
    const isMobile = window.innerWidth <= 767;
    const margin = { top: 20, right: 120, bottom: 40, left: 100 };
    const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
    const height = 250 - margin.top - margin.bottom;

    const svg = container.append('svg')
      .attr('viewBox', `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);
      
    data.sort((a, b) => b.percent - a.percent);

    const yScale = d3.scaleBand()
      .domain(data.map(d => d.name))
      .range([0, height])
      .padding(0.1);

    const xScale = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.percent)])
      .range([0, width]);

    svg.append('g')
      .call(d3.axisLeft(yScale));

    svg.append('g')
      .attr('transform', `translate(0, ${height})`)
      .call(d3.axisBottom(xScale).ticks(5).tickFormat(d => `${d}%`));

    svg.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('y', d => yScale(d.name))
      .attr('width', d => xScale(d.percent))
      .attr('height', yScale.bandwidth())
      .attr('fill', d => pitchColor(d.pitchType));

    svg.selectAll('.label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'label')
      .attr('y', d => yScale(d.name) + yScale.bandwidth() / 2)
      .attr('x', d => xScale(d.percent) > 80 ? xScale(d.percent) - 5 : xScale(d.percent) + 5)
      .attr('dy', '.35em')
      .attr('text-anchor', d => xScale(d.percent) > 80 ? 'end' : 'start')
      .style('fill', d => xScale(d.percent) > 80 ? 'white' : '#333')
      .style('font-family', 'Roboto, sans-serif')
      .style('font-size', '11px')
      .style('font-weight', '500')
      .text((d, i) => {
        if (i === 0) { // First bar (highest percentage)
          return `${d.percent.toFixed(1)}% (avg ${d.avg_vel.toFixed(1)} mph)`;
      } else {
          return `${d.percent.toFixed(1)}% (${d.avg_vel.toFixed(1)})`;
        }
      });
  }

  function renderOhtaniPitchLocation(data) {
    const container = d3.select('#shohei-pitch-location-chart');
    container.selectAll('*').remove();
    container.append('h3').attr('class', 'visual-subhead').text('Pitch Locations');

    // Fixed SVG size and coordinate system
    const svgSize = 350;
    const svg = container.append('svg')
      .attr('width', svgSize)
      .attr('height', svgSize)
      .attr('viewBox', `0 0 ${svgSize} ${svgSize}`);

    // Savant-style scales: x [-2.5, 2.5] -> [0, 350], z [0.5, 4.5] -> [315, 35]
    const xScale = d3.scaleLinear().domain([-2.5, 2.5]).range([0, svgSize]);
    const yScale = d3.scaleLinear().domain([0.5, 4.5]).range([315, 35]);

    // Strike zone: x [-0.71, 0.71], z [1.5, 3.5]
    const szLeft = xScale(-0.71);
    const szRight = xScale(0.71);
    const szTop = yScale(3.5);
    const szBot = yScale(1.5);
    const szWidth = szRight - szLeft;
    const szHeight = szBot - szTop;

    svg.append('rect')
      .attr('x', szLeft)
      .attr('y', szTop)
      .attr('width', szWidth)
      .attr('height', szHeight)
      .attr('fill', 'none')
      .attr('stroke', '#666')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4,4');

    // Improved home plate (wider, flatter, more space below zone)
    const plateWidth = szWidth;
    const plateHeight = 18; // Flatter plate
    const plateY = szBot + 22; // More space below zone
    const plateX = szLeft;
    const platePath = [
      [plateX + plateWidth * 0.2, plateY], // left notch
      [plateX + plateWidth * 0.8, plateY], // right notch
      [plateX + plateWidth, plateY + plateHeight * 0.4], // right corner
      [plateX + plateWidth / 2, plateY + plateHeight], // bottom point
      [plateX, plateY + plateHeight * 0.4], // left corner
      [plateX + plateWidth * 0.2, plateY] // close path
    ];
    svg.append('polygon')
      .attr('points', platePath.map(p => p.join(",")).join(" "))
      .attr('fill', '#e0e0e0')
      .attr('stroke', '#666')
      .attr('stroke-width', 1);

    // Draw pitches
    svg.selectAll('.pitch')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'pitch')
      .attr('cx', d => xScale(d.x))
      .attr('cy', d => yScale(d.z))
      .attr('r', 5)
      .attr('fill', d => pitchColor(d.pitch_type_abbr))
      .attr('opacity', 0.8)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1);
  }

  fetchOhtaniPitchData();
});

// Playoff Bracket Functions
async function fetchPlayoffBracketData() {
  try {
    const currentYear = new Date().getFullYear();
    const response = await fetch(`https://stilesdata.com/dodgers/data/standings/all_teams_standings_metrics_${currentYear}.json`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    // Handle both old format (array) and new format (object with metadata)
    if (Array.isArray(data)) {
      return { teams: data, last_updated: null };
    } else if (data.teams) {
      return data;
    } else {
      console.error('Unexpected data format:', data);
      return null;
    }
  } catch (error) {
    console.error('Error fetching playoff bracket data:', error);
    return null;
  }
}

function calculatePlayoffSeeds(standings) {
  // Separate leagues
  const nlTeams = standings.filter(team => team.league_name === 'National League');
  const alTeams = standings.filter(team => team.league_name === 'American League');
  
  // Sort by division rank first, then by league rank for wild cards
  function getPlayoffTeams(leagueTeams) {
    // Get division winners (rank 1 in each division)
    const divisionWinners = leagueTeams
      .filter(team => team.division_rank === '1')
      .sort((a, b) => parseFloat(b.winning_percentage) - parseFloat(a.winning_percentage));
    
    // Get wild card teams (best non-division winners)
    const wildCardCandidates = leagueTeams
      .filter(team => team.division_rank !== '1')
      .sort((a, b) => parseFloat(b.winning_percentage) - parseFloat(a.winning_percentage));
    
    const wildCards = wildCardCandidates.slice(0, 3); // Top 3 wild cards
    
    // Assign seeds: division winners get 1-3, wild cards get 4-6
    const playoffTeams = [];
    
    // Division winners get seeds 1-3
    divisionWinners.forEach((team, index) => {
      playoffTeams.push({
        ...team,
        seed: index + 1
      });
    });
    
    // Wild cards get seeds 4-6
    wildCards.forEach((team, index) => {
      playoffTeams.push({
        ...team,
        seed: index + 4
      });
    });
    
    return playoffTeams;
  }
  
  return {
    nl: getPlayoffTeams(nlTeams),
    al: getPlayoffTeams(alTeams)
  };
}

function getTeamAbbreviation(teamName) {
  const abbrevMap = {
    'Los Angeles Dodgers': 'LAD',
    'New York Yankees': 'NYY',
    'Los Angeles Angels': 'LAA',
    'Houston Astros': 'HOU',
    'Atlanta Braves': 'ATL',
    'New York Mets': 'NYM',
    'Philadelphia Phillies': 'PHI',
    'San Diego Padres': 'SD',
    'San Francisco Giants': 'SF',
    'Milwaukee Brewers': 'MIL',
    'St. Louis Cardinals': 'STL',
    'Chicago Cubs': 'CHC',
    'Arizona Diamondbacks': 'ARI',
    'Colorado Rockies': 'COL',
    'Toronto Blue Jays': 'TOR',
    'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS',
    'Tampa Bay Rays': 'TB',
    'Cleveland Guardians': 'CLE',
    'Detroit Tigers': 'DET',
    'Kansas City Royals': 'KC',
    'Minnesota Twins': 'MIN',
    'Chicago White Sox': 'CWS',
    'Texas Rangers': 'TEX',
    'Seattle Mariners': 'SEA',
    'Oakland Athletics': 'OAK',
    'Pittsburgh Pirates': 'PIT',
    'Cincinnati Reds': 'CIN',
    'Miami Marlins': 'MIA',
    'Washington Nationals': 'WSN'
  };
  return abbrevMap[teamName] || teamName.substring(0, 3).toUpperCase();
}

function getTeamMascot(teamName) {
  // Extract just the mascot/nickname from full team name
  const mascotMap = {
    'Los Angeles Dodgers': 'Dodgers',
    'New York Yankees': 'Yankees', 
    'Los Angeles Angels': 'Angels',
    'Houston Astros': 'Astros',
    'Atlanta Braves': 'Braves',
    'New York Mets': 'Mets',
    'Philadelphia Phillies': 'Phillies',
    'San Diego Padres': 'Padres',
    'San Francisco Giants': 'Giants',
    'Milwaukee Brewers': 'Brewers',
    'St. Louis Cardinals': 'Cardinals',
    'Chicago Cubs': 'Cubs',
    'Arizona Diamondbacks': 'Diamondbacks',
    'Colorado Rockies': 'Rockies',
    'Toronto Blue Jays': 'Blue Jays',
    'Baltimore Orioles': 'Orioles',
    'Boston Red Sox': 'Red Sox',
    'Tampa Bay Rays': 'Rays',
    'Cleveland Guardians': 'Guardians',
    'Detroit Tigers': 'Tigers',
    'Kansas City Royals': 'Royals',
    'Minnesota Twins': 'Twins',
    'Chicago White Sox': 'White Sox',
    'Texas Rangers': 'Rangers',
    'Seattle Mariners': 'Mariners',
    'Oakland Athletics': 'Athletics',
    'Pittsburgh Pirates': 'Pirates',
    'Cincinnati Reds': 'Reds',
    'Miami Marlins': 'Marlins',
    'Washington Nationals': 'Nationals'
  };
  
  return mascotMap[teamName] || teamName.split(' ').pop(); // Fallback to last word
}

function getTeamLogoUrl(teamId) {
  return `https://midfield.mlbstatic.com/v1/team/${teamId}/spots/`;
}

function populateTeamSlot(element, team) {
  if (!team) return;
  
  const teamAbbr = getTeamAbbreviation(team.team_name);
  const teamMascot = getTeamMascot(team.team_name);
  const teamLogo = element.querySelector('.team-logo');
  const teamName = element.querySelector('.team-name');
  const teamSeed = element.querySelector('.team-seed');
  
  // Update team info - use mascot name for better readability
  teamName.textContent = teamMascot;
  teamSeed.textContent = team.seed;
  
  // Add record display (wins-losses) - create element if it doesn't exist
  let teamRecord = element.querySelector('.team-record');
  if (!teamRecord) {
    teamRecord = document.createElement('span');
    teamRecord.className = 'team-record';
    // Insert between team name and seed
    teamName.parentNode.insertBefore(teamRecord, teamSeed);
  }
  teamRecord.textContent = `(${team.wins}-${team.losses})`;
  
  // Add team-specific styling
  teamLogo.setAttribute('data-team', teamAbbr);
  
  // Set team logo as background image
  const logoUrl = getTeamLogoUrl(team.team_id);
  teamLogo.style.backgroundImage = `url('${logoUrl}')`;
  teamLogo.style.backgroundSize = 'contain';
  teamLogo.style.backgroundRepeat = 'no-repeat';
  teamLogo.style.backgroundPosition = 'center';
  teamLogo.textContent = ''; // Remove text content since we have logo now
  
  // Fallback: if logo fails to load, show abbreviation
  const logoImg = new Image();
  logoImg.onload = function() {
    // Logo loaded successfully, keep it
  };
  logoImg.onerror = function() {
    // Logo failed to load, show text fallback
    teamLogo.style.backgroundImage = '';
    teamLogo.textContent = teamAbbr.substring(0, 2);
  };
  logoImg.src = logoUrl;
  
  // Special styling for Dodgers
  if (teamAbbr === 'LAD') {
    element.classList.add('dodgers-team');
  }
}

function renderPlayoffBracket(playoffTeams) {
  const { nl, al } = playoffTeams;
  
  // Populate NL bracket
  const nlBracket = document.querySelector('.nl-bracket');
  if (nlBracket && nl.length >= 6) {
    // Wild Card round
    populateTeamSlot(nlBracket.querySelector('[data-seed="6"]'), nl.find(t => t.seed === 6));
    populateTeamSlot(nlBracket.querySelector('[data-seed="3"]'), nl.find(t => t.seed === 3));
    populateTeamSlot(nlBracket.querySelector('[data-seed="5"]'), nl.find(t => t.seed === 5));
    populateTeamSlot(nlBracket.querySelector('[data-seed="4"]'), nl.find(t => t.seed === 4));
    
    // Division Series
    populateTeamSlot(nlBracket.querySelector('[data-seed="1"]'), nl.find(t => t.seed === 1));
    populateTeamSlot(nlBracket.querySelector('[data-seed="2"]'), nl.find(t => t.seed === 2));
  }
  
  // Populate AL bracket
  const alBracket = document.querySelector('.al-bracket');
  if (alBracket && al.length >= 6) {
    // Wild Card round
    populateTeamSlot(alBracket.querySelector('[data-seed="6"]'), al.find(t => t.seed === 6));
    populateTeamSlot(alBracket.querySelector('[data-seed="3"]'), al.find(t => t.seed === 3));
    populateTeamSlot(alBracket.querySelector('[data-seed="5"]'), al.find(t => t.seed === 5));
    populateTeamSlot(alBracket.querySelector('[data-seed="4"]'), al.find(t => t.seed === 4));
    
    // Division Series
    populateTeamSlot(alBracket.querySelector('[data-seed="1"]'), al.find(t => t.seed === 1));
    populateTeamSlot(alBracket.querySelector('[data-seed="2"]'), al.find(t => t.seed === 2));
  }
}

function displayLastUpdated(lastUpdated) {
  if (!lastUpdated) return;
  
  // Create or update the last updated element
  let lastUpdatedElement = document.getElementById('playoff-last-updated');
  if (!lastUpdatedElement) {
    lastUpdatedElement = document.createElement('p');
    lastUpdatedElement.id = 'playoff-last-updated';
    lastUpdatedElement.className = 'note';
    
    const bracketContainer = document.getElementById('playoff-bracket-container');
    if (bracketContainer) {
      bracketContainer.appendChild(lastUpdatedElement);
    }
  }
  
  lastUpdatedElement.textContent = `Last updated on ${lastUpdated}`;
}

async function initPlayoffBracket() {
  try {
    const standingsData = await fetchPlayoffBracketData();
    if (standingsData && standingsData.teams && standingsData.teams.length > 0) {
      const playoffTeams = calculatePlayoffSeeds(standingsData.teams);
      renderPlayoffBracket(playoffTeams);
      
      // Display last updated timestamp
      if (standingsData.last_updated) {
        displayLastUpdated(standingsData.last_updated);
      }
    } else {
      console.log('No standings data available for playoff bracket');
    }
  } catch (error) {
    console.error('Error initializing playoff bracket:', error);
  }
}

// Initialize playoff bracket when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  if (document.getElementById('playoff-bracket-container')) {
    initPlayoffBracket();
  }
});

