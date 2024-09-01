
// Games back line chart

async function fetchData() {
  try {
    const response = await d3.json(
      'https://stilesdata.com/dodgers/data/standings/dodgers_standings_1958_present_optimized.json'
    );
    // Group data by year
    const groupedByYear = d3.group(response, (d) => d.year);
    renderChart(groupedByYear);
  } catch (error) {
    console.error('Failed to fetch data:', error);
  }
}

function renderChart(data) {
  const isMobile = window.innerWidth <= 767; // Example breakpoint for mobile devices
  const margin = isMobile 
    ? { top: 20, right: 0, bottom: 60, left: 50 }  // Smaller margins for mobile
    : { top: 20, right: 0, bottom: 50, left: 60 }; // Larger margins for desktop
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

    const xScale = d3
    .scaleLinear()
    .domain([0, 166])
    .range([0, width]);

  const yScale = d3
    .scaleLinear()
    .domain([
      d3.min(Array.from(data.values()).flat(), (d) => d.gb),
      d3.max(Array.from(data.values()).flat(), (d) => d.gb),
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
      .text("Games up/back");

  // Append axes to SVG
  svg
    .append('g')
    .attr('transform', `translate(0, ${height})`)
    .call(xAxis)
    .selectAll('line') // Select all lines which includes ticks and optionally grid lines
    .style('stroke', '#ddd'); // Light gray for a softer look

  svg.append('g').call(yAxis).selectAll('line').style('stroke', '#ddd');

  svg
    .selectAll('.domain') // This selects the domain line of the axes
    .style('stroke', '#e9e9e9'); // Light grey color

  const line = d3
    .line()
    .x((d) => xScale(d.gm))
    .y((d) => yScale(d.gb))
    .curve(d3.curveMonotoneX); // Smooth the line

  // Draw all lines except 2024 first
  const allLinesExcept2024 = Array.from(data.entries()).filter(
    (d) => d[0] !== '2024'
  );
  svg
    .selectAll('.line')
    .data(allLinesExcept2024, (d) => d[0])
    .enter()
    .append('path')
    .attr('class', 'line')
    .attr('d', (d) => line(d[1]))
    .style('fill', 'none')
    .style('stroke', '#ccc')
    .style('stroke-width', 0.5);

  const line2024 = Array.from(data.entries()).filter((d) => d[0] === '2024');
  svg
    .selectAll('.line-2024')
    .data(line2024, (d) => d[0])
    .enter()
    .append('path')
    .attr('class', 'line')
    .attr('d', (d) => line(d[1]))
    .style('fill', 'none')
    .style('stroke', '#005A9C')
    .style('stroke-width', 2);

  // Add a horizontal line at y = 0
  svg
    .append('line')
    .attr('x1', 0)
    .attr('x2', isMobile ? width-7 : width-18)
    .attr('y1', yScale(0))
    .attr('y2', yScale(0))
    .attr('stroke', '#222')
    .attr('stroke-width', 1);

  // Add the 'Leading' annotation
  svg
    .append('text')
    .attr('x', isMobile ? xScale(75) : xScale(70)) // Adjusted for mobile
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

  // Add the 'Past ' annotation
  svg
    .append('text')
    .attr('x', isMobile ? xScale(80) : xScale(110)) // Adjusted for mobile
    .attr('y', yScale(22))
    .attr('class', 'anno')
    .text('Past: 1958-2023')
    .attr('text-anchor', 'start');

  const lastData2024 = data.get('2024').slice(0)[0];
  // console.log(lastData2024);

  svg
    .append('text')
    .attr('x', xScale(lastData2024.gm + 1))
    .attr('y', yScale(lastData2024.gb) - 12)
    .text('2024')
    .attr('class', 'anno-dodgers')
    .style('stroke', '#fff')
    .style('stroke-width', '4px')
    .style('stroke-linejoin', 'round')
    .attr('text-anchor', 'start')
    .style('paint-order', 'stroke')
    .clone(true)
    .style('stroke', 'none');

  function gameStatusText(gamesBack) {
    if (gamesBack > 0) {
      return gamesBack + ' games up';
    } else if (gamesBack < 0) {
      return -gamesBack + ' games back';
    } else {
      return ' games back';
    }
  }

  svg
    .append('text')
    .attr('x', xScale(lastData2024.gm + 1))
    .attr('y', yScale(lastData2024.gb) + 2)
    .text(gameStatusText(lastData2024.gb))
    .attr('class', 'anno-dark')
    .style('stroke', '#fff')
    .style('stroke-width', '4px')
    .style('stroke-linejoin', 'round')
    .attr('text-anchor', 'start')
    .style('paint-order', 'stroke')
    .clone(true)
    .style('stroke', 'none');
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
  const margin = isMobile ? { top: 20, right: 10, bottom: 50, left: 30 } : { top: 20, right: 20, bottom: 40, left: 40 };
  const container = d3.select('#results-chart');
  const containerWidth = container.node().getBoundingClientRect().width;
  const width = containerWidth - margin.left - margin.right;
  const height = 200 - margin.top - margin.bottom;

  const svg = container.append('svg')
    .attr('width', containerWidth)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const xScale = d3.scaleBand()
    .range([0, width])
    .padding(0.1)
    .domain(data.map(d => d.gm));

  const yScale = d3.scaleLinear()
    .range([height, 0])
    .domain([d3.min(data, d => d.run_diff), d3.max(data, d => d.run_diff)]);

  const xAxis = d3.axisBottom(xScale).tickValues(xScale.domain().filter(d => d % 10 === 0));
  const yAxis = d3.axisLeft(yScale).ticks(5);

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(xAxis);

  svg.append('g').call(yAxis);

      // X-axis Label
      svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 5)
      .text("Game number");
  
    // Y-axis Label
    svg.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("transform", "rotate(-90)")
      .attr("y", -margin.left + 10)
      .attr("x", -height / 2)
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

      // Draw all lines except the current year first
      const allLinesExceptCurrentYear = Array.from(data.entries()).filter(
          (d) => d[0] !== currentYear && d[0] !== selectedYear
      );

      svg.selectAll('.line').remove(); // Clear previous lines
      svg.selectAll('.anno-selected-year').remove(); // Clear previous annotations

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

      // Draw the selected year line if a year is selected
      if (selectedYear) {
          const selectedYearData = Array.from(data.entries()).filter((d) => d[0] === selectedYear);
          // console.log('Selected Year Data:', selectedYearData);

          if (selectedYearData.length > 0) {
              // Sort the data to ensure we get the last game correctly
              selectedYearData[0][1].sort((a, b) => d3.ascending(a.gm, b.gm));
              const selectedYearLastData = selectedYearData[0][1].slice(-1)[0];
              // console.log('Selected Year Last Data:', selectedYearLastData);

              svg
                  .selectAll('.line-selected-year')
                  .data(selectedYearData, (d) => d[0])
                  .enter()
                  .append('path')
                  .attr('class', 'line line-selected-year')
                  .attr('d', (d) => line(d[1]))
                  .style('fill', 'none')
                  .style('stroke', '#ef3e42') // Dodger Red
                  .style('stroke-width', 1.5);

              // Add text annotation for the selected year
              svg
                  .append('text')
                  .attr('x', xScale(selectedYearLastData.gm) - 10) // Adjusted x position
                  .attr('y', yScale(selectedYearLastData.wins) - 10) // Adjusted y position
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
      svg
          .selectAll('.line-current-year')
          .data(lineCurrentYear, (d) => d[0])
          .enter()
          .append('path')
          .attr('class', 'line line-current-year')
          .attr('d', (d) => line(d[1]))
          .style('fill', 'none')
          .style('stroke', '#005A9C')
          .style('stroke-width', 2);

      // Ensure lastDataCurrentYear is set to the last game
      lineCurrentYear[0][1].sort((a, b) => d3.ascending(a.gm, b.gm));
      const lastDataCurrentYear = lineCurrentYear[0][1].slice(-1)[0];
      // console.log('Last Data Current Year:', lastDataCurrentYear);

      svg
          .append('text')
          .attr('x', xScale(lastDataCurrentYear.gm) + 5) // Adjusted x position
          .attr('y', yScale(lastDataCurrentYear.wins) - 10) // Adjusted y position
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
          .attr('x', xScale(lastDataCurrentYear.gm) + 5) // Adjusted x position
          .attr('y', yScale(lastDataCurrentYear.wins) + 2) // Adjusted y position
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

  function updateChart() {
      const svg = d3.select('#cumulative-wins-chart svg g');
      drawLines(svg, groupedByYear);
  }

  function renderCumulativeWinsChart(data) {
      const isMobile = window.innerWidth <= 767; // Example breakpoint for mobile devices
      const margin = isMobile 
          ? { top: 20, right: 20, bottom: 60, left: 60 }  // Smaller margins for mobile
          : { top: 20, right: 20, bottom: 50, left: 60 }; // Larger margins for desktop
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
          .attr("y", -margin.left + 20)
          .attr("x", -height / 2)
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
          ? { top: 20, right: 20, bottom: 60, left: 60 } 
          : { top: 20, right: 20, bottom: 50, left: 60 };
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
            // console.log(`Rendering line for year ${d[0]} with data:`, d[1]);
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
            .attr('d', (d) => {
              // console.log(`Rendering current year line for year ${d[0]} with data:`, d[1]);
              return line(d[1]);
            })
            .style('fill', 'none')
            .style('stroke', '#005A9C')
            .style('stroke-width', 2);
        }
    
        svg
          .append('text')
          .attr('x', isMobile ? xScale(100) : xScale(100))
          .attr('y', yScale(300))
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
      ? { top: 20, right: 20, bottom: 60, left: 70 } 
      : { top: 20, right: 20, bottom: 50, left: 70 };
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
      .attr('x', isMobile ? xScale(90) : xScale(100))
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
      // console.log('Fetched data:', response);
      // Group data by year
      const groupedByYear = d3.group(response, (d) => d.year.toString());
      // console.log('Grouped data by year:', groupedByYear);
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
    // console.log('All lines except current year:', allLinesExceptCurrentYear);

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
    // console.log('Current year:', currentYear);
    const lineCurrentYear = data.get(currentYear);
    // console.log('Current year data:', lineCurrentYear);

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
      // console.log('Last data of current year:', lastDataCurrentYear);

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
      .text(`Past seasons: 1958-${currentYear - 1}`)
      .attr('text-anchor', 'start');
  }

  fetchCumulativeERAData();
});




// TABLES
// Schedule

document.addEventListener('DOMContentLoaded', function () {
  const renderTable = (games, tableId) => {
    const tableBody = document.querySelector(`#${tableId} tbody`);
    tableBody.innerHTML = '';

    games.forEach(game => {
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
      .each(function (d) {
        const barWidth = (d.attend_game / maxAttendance) * 100;
        const isDodgers = d.team === 'Los Angeles Dodgers';
        d3.select(this).append('div')
          .attr('class', `attendance-bar-bg ${isDodgers ? 'attendance-bar-dodgers' : ''}`)
          .style('width', `${barWidth}%`);
        d3.select(this).append('div')
          .attr('class', `attendance-bar-text ${isDodgers ? 'attendance-bar-dodgers' : ''}`)
          .text(d.attend_game.toLocaleString());
      });
  }

  function renderMaxAttendanceInfo(data) {
    const maxAttendanceTeam = data.reduce((max, team) => (team.attend_game > max.attend_game ? team : max), data[0]);
    const maxAttendanceText = `The average attendance to see the ${maxAttendanceTeam.team} at ${maxAttendanceTeam.name} so far this season is ${maxAttendanceTeam.attend_game.toLocaleString()}, more than any other franchise in Major League Baseball.`;

    // Insert the text into a paragraph element
    d3.select('#max-attendance-info').text(maxAttendanceText);
  }

  fetchTableData();
});




document.addEventListener('DOMContentLoaded', function() {
  let eventsData = [];
  const eventsSet = new Set();
  const selectMenu = document.getElementById('event-select');

  async function fetchPlayerAtBatData() {
    try {
      const response = await fetch('https://stilesdata.com/dodgers/data/batting/dodgers_player_atbat_lastpitch_outcome_current.json');
      eventsData = await response.json();
      
      // Collect unique event types
      eventsData.forEach(d => eventsSet.add(d.events));
      populateEventSelect(Array.from(eventsSet));
      
      // Initially render the chart with the default event type
      renderBarCodeChart('Home run');
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  }

  function populateEventSelect(events) {
    events.forEach(event => {
      const option = document.createElement('option');
      option.value = event;
      option.text = event;
      selectMenu.appendChild(option);
    });

    selectMenu.addEventListener('change', function() {
      renderBarCodeChart(this.value);
    });
  }

  fetchPlayerAtBatData();
  
  function renderBarCodeChart(selectedEvent) {
    const container = d3.select('#barcode-chart');
    const svg = container.select('svg');
    svg.selectAll('*').remove(); // Clear previous chart

    const isMobile = window.innerWidth <= 767;

    const margin = isMobile 
    ? { top: 20, right: 0, bottom: 60, left: 120 }  // Smaller margins for mobile
    : { top: 20, right: 0, bottom: 50, left: 120 }; // Larger margins for desktop

    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - margin.left - margin.right;
    const height = 500 - margin.top - margin.bottom;

    svg.attr('viewBox', `0 0 ${containerWidth} 500`).attr('preserveAspectRatio', 'xMinYMin meet');

    // Filter and sort data by plate appearances
    const sortedData = d3.rollups(eventsData, v => d3.max(v, d => d.pa_number), d => d.batter_name_clean)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(d => d[0]);

    const filteredData = eventsData.filter(d => sortedData.includes(d.batter_name_clean));

    const x = d3.scaleLinear()
      .domain([0, d3.max(filteredData, d => d.pa_number)])
      .range([0, width]);

    const y = d3.scaleBand()
      .domain(filteredData.map(d => d.batter_name_clean).filter((v, i, a) => a.indexOf(v) === i))
      .range([0, height])
      .padding(0.1);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const xAxis = d3.axisBottom(x).tickValues(x.ticks(isMobile ? 50 : 25).filter(tick => tick % (isMobile ? 50 : 25) === 0));

    g.append('g')
      .attr('class', 'axis axis--x')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis);

    g.append('g')
      .attr('class', 'axis axis--y')
      .call(d3.axisLeft(y));

    // X-axis Label
    g.append("text")
      .attr("text-anchor", "middle")
      .attr('class', 'anno-dark')
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 10)
      .text("Plate appearance number");

    // Draw gray lines for all events
    g.selectAll('.line')
      .data(filteredData)
      .enter()
      .append('line')
      .attr('x1', d => x(d.pa_number))
      .attr('x2', d => x(d.pa_number))
      .attr('y1', d => y(d.batter_name_clean))
      .attr('y2', d => y(d.batter_name_clean) + y.bandwidth())
      .attr('stroke', '#ccc')
      .attr('stroke-width', .3);

    // Highlight selected event type with color based on positive_outcome
    g.selectAll('.highlight')
      .data(filteredData.filter(d => d.events === selectedEvent))
      .enter()
      .append('line')
      .attr('x1', d => x(d.pa_number))
      .attr('x2', d => x(d.pa_number))
      .attr('y1', d => y(d.batter_name_clean))
      .attr('y2', d => y(d.batter_name_clean) + y.bandwidth())
      .attr('stroke', d => d.positive_outcome ? '#005A9C' : '#ef3e42')
      .attr('stroke-width', 1);

    // pitch annotation line and text
    const annotationX = x(40); 
    const annotationY = y('Freddie Freeman') + y.bandwidth() / 2;

    g.append('line')
      .attr('x1', annotationX)
      .attr('x2', annotationX)
      .attr('y1', annotationY - 40)
      .attr('y2', annotationY - 25)
      .attr('stroke', '#000')
      .attr('stroke-width', 1)
      .attr('marker-end', 'url(#arrow)');

    g.append('text')
      .attr('x', annotationX + 10)
      .attr('y', annotationY - 30)
      .attr('text-anchor', 'start')
      .attr('font-size', '12px')
      .attr('fill', '#222')
      .text('Line = plate appearance')
      .attr('class', 'anno-dark');

    // Define the arrow marker
    svg.append('defs')
      .append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 5)
      .attr('refY', 5)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z')
      .attr('fill', '#000');
  }

  window.addEventListener('resize', () => renderBarCodeChart(selectMenu.value));
});


