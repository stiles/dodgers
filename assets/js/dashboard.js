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
    ? { top: 20, right: 20, bottom: 60, left: 60 }  // Smaller margins for mobile
    : { top: 40, right: 50, bottom: 50, left: 60 }; // Larger margins for desktop
  const container = d3.select('#d3-container');
  const containerWidth = container.node().getBoundingClientRect().width;
  const width = containerWidth - margin.left - margin.right;
  const height = isMobile 
  ? Math.round(width * 1) - margin.top - margin.bottom  // Taller  for mobile
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
    .attr('x2', width-18)
    .attr('y1', yScale(0))
    .attr('y2', yScale(0))
    .attr('stroke', '#222')
    .attr('stroke-width', 1);

  svg
    .append('text')
    .attr('x', xScale(150))
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

  svg
    .append('text')
    .attr('x', xScale(110))
    .attr('y', yScale(22))
    .attr('class', 'anno')
    .text('Past seasons: 1958-2023')
    .attr('text-anchor', 'start');

  const lastData2024 = data.get('2024').slice(0)[0];
  console.log(lastData2024);

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