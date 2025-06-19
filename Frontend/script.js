// Global variables
let chartInstances = {};
let dataRefreshInterval;
const DATA_REFRESH_RATE = 30000; // 30 seconds

// DOM Elements
const elements = {
  roomCards: document.getElementById('roomCards'),
  overviewChart: document.getElementById('overviewChart'),
  roomSelect: document.getElementById('roomSelect'),
  detailsChart: document.getElementById('detailsChart'),
  dataTableContainer: document.getElementById('dataTableContainer')
};

// Initialize the application
async function init() {
  try {
    // Load initial data
    const data = await fetchData();
    
    // Update UI based on current page
    if (elements.roomCards) {
      // Dashboard page
      updateRoomCards(data);
      drawOverviewChart(data);
      setupDataRefresh();
    } else if (elements.detailsChart) {
      // Details page
      populateRoomSelector(data);
      setupDataRefresh();
    }
  } catch (error) {
    console.error('Error initializing application:', error);
    showError('Failed to load data. Please try again later.');
  }
}

// Fetch data from server
async function fetchData() {
  try {
    const response = await fetch('testi.json');
    if (!response.ok) throw new Error('Network response was not ok');
    return await response.json();
  } catch (error) {
    console.error('Error fetching data:', error);
    throw error;
  }
}

// Set up periodic data refresh
function setupDataRefresh() {
  clearInterval(dataRefreshInterval);
  dataRefreshInterval = setInterval(async () => {
    try {
      const newData = await fetchData();
      if (elements.roomCards) {
        updateRoomCards(newData);
        updateChart(chartInstances.overview, newData);
      } else if (elements.detailsChart) {
        const selectedRoom = elements.roomSelect?.value || 'all';
        updateDetails(newData, selectedRoom);
      }
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  }, DATA_REFRESH_RATE);
}

// AQI level calculation (1-5)
function aqiLevel(aqi) {
  if (aqi <= 50) return 1;
  if (aqi <= 100) return 2;
  if (aqi <= 150) return 3;
  if (aqi <= 200) return 4;
  return 5;
}

// AQI level to color
function aqiColor(level) {
  const colors = [
    "#4caf50", // green (level 1)
    "#ffeb3b", // yellow (level 2)
    "#ff9800", // orange (level 3)
    "#f44336", // red (level 4)
    "#9c27b0"  // purple (level 5)
  ];
  return colors[level - 1] || "#bdbdbd";
}

// Create AQI gauge for a room
function createAQIGauge(room, aqi, temperature) {
  const level = aqiLevel(aqi);
  const color = aqiColor(level);
  const rotation = (level - 1) * 45;

  return `
    <div class="card fade-in">
      <a href="details.html?room=${encodeURIComponent(room)}" class="card-link">
        <div class="gauge-container">
          <div class="gauge"></div>
          <div class="needle" style="transform: rotate(${rotation}deg);"></div>
          <div class="gauge-center">
            <div class="gauge-label">${room}</div>
            <div class="gauge-value" style="color: ${color}">${aqi} AQI</div>
            <div class="gauge-subvalue">${temperature} °C</div>
          </div>
        </div>
      </a>
    </div>
  `;
}

// Update room cards on dashboard
function updateRoomCards(data) {
  if (!elements.roomCards) return;

  // Get latest reading for each room
  const latestReadings = data.reduce((acc, reading) => {
    if (!acc[reading.room] || new Date(reading.timestamp) > new Date(acc[reading.room].timestamp)) {
      acc[reading.room] = reading;
    }
    return acc;
  }, {});

  // Create HTML for each room
  const cardsHTML = Object.values(latestReadings)
    .map(roomData => createAQIGauge(roomData.room, roomData.aqi, roomData.temperature))
    .join('');

  // Update DOM efficiently
  elements.roomCards.innerHTML = cardsHTML;
}

// Draw or update overview chart
function drawOverviewChart(data) {
  if (!elements.overviewChart) return;

  const rooms = [...new Set(data.map(d => d.room))];
  const datasets = rooms.map((room, i) => {
    const roomData = data.filter(d => d.room === room).sort((a, b) => 
      new Date(a.timestamp) - new Date(b.timestamp)
    );
    
    return {
      label: `${room} AQI`,
      data: roomData.map(d => ({ 
        x: new Date(d.timestamp), 
        y: d.aqi 
      })),
      borderColor: `hsl(${i * (360 / rooms.length)}, 70%, 50%)`,
      backgroundColor: `hsla(${i * (360 / rooms.length)}, 70%, 50%, 0.1)`,
      borderWidth: 2,
      tension: 0.3,
      fill: true,
      pointRadius: 0
    };
  });

  // Destroy previous instance if exists
  if (chartInstances.overview) {
    chartInstances.overview.destroy();
  }

  chartInstances.overview = new Chart(elements.overviewChart, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'hour',
            displayFormats: {
              hour: 'HH:mm'
            }
          },
          title: {
            display: true,
            text: 'Time'
          },
          grid: {
            display: false
          }
        },
        y: {
          title: {
            display: true,
            text: 'AQI'
          },
          min: 0,
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            label: (context) => {
              const label = context.dataset.label || '';
              const value = context.parsed.y;
              return `${label}: ${value} AQI`;
            }
          }
        },
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            padding: 20,
            usePointStyle: true
          }
        }
      },
      animation: {
        duration: 1000,
        easing: 'easeOutQuart'
      }
    }
  });
}

// Populate room selector dropdown
function populateRoomSelector(data) {
  if (!elements.roomSelect) return;

  // Get room parameter from URL
  const params = new URLSearchParams(window.location.search);
  const selectedRoom = params.get('room') || "all";

  // Get unique rooms
  const rooms = [...new Set(data.map(d => d.room))];
  
  // Clear and repopulate dropdown
  elements.roomSelect.innerHTML = '';
  
  // Add "All Rooms" option
  const allOption = document.createElement('option');
  allOption.value = 'all';
  allOption.textContent = 'All Rooms';
  elements.roomSelect.appendChild(allOption);
  
  // Add room options
  rooms.forEach(room => {
    const option = document.createElement('option');
    option.value = room;
    option.textContent = room;
    elements.roomSelect.appendChild(option);
  });

  // Set selected room
  elements.roomSelect.value = selectedRoom;
  
  // Add event listener
  elements.roomSelect.addEventListener('change', () => {
    updateDetails(data, elements.roomSelect.value);
  });

  // Initial update
  updateDetails(data, selectedRoom);
}

// Update details view (chart and table)
function updateDetails(data, room) {
  if (!elements.detailsChart || !elements.dataTableContainer) return;

  // Filter data based on selected room
  const filteredData = room === 'all' 
    ? [...data].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    : data.filter(d => d.room === room)
          .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  // Update chart
  updateDetailsChart(filteredData, room);
  
  // Update table
  updateDetailsTable(filteredData);
}

// Update details chart
function updateDetailsChart(data, room) {
  const labels = data.map(d => new Date(d.timestamp));
  
  const datasets = [
    {
      label: 'AQI',
      data: data.map(d => d.aqi),
      borderColor: '#3f51b5',
      backgroundColor: 'rgba(63, 81, 181, 0.1)',
      borderWidth: 2,
      tension: 0.3,
      yAxisID: 'y'
    },
    {
      label: 'Temperature (°C)',
      data: data.map(d => d.temperature),
      borderColor: '#ff9800',
      backgroundColor: 'rgba(255, 152, 0, 0.1)',
      borderWidth: 2,
      tension: 0.3,
      yAxisID: 'y1'
    },
    {
      label: 'CO₂ (ppm)',
      data: data.map(d => d.co2),
      borderColor: '#4caf50',
      backgroundColor: 'rgba(76, 175, 80, 0.1)',
      borderWidth: 2,
      tension: 0.3,
      yAxisID: 'y2'
    }
  ];

  // Destroy previous instance if exists
  if (chartInstances.details) {
    chartInstances.details.destroy();
  }

  chartInstances.details = new Chart(elements.detailsChart, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'hour',
            displayFormats: {
              hour: 'HH:mm'
            }
          },
          title: {
            display: true,
            text: 'Time'
          },
          grid: {
            display: false
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: {
            display: true,
            text: 'AQI'
          },
          grid: {
            drawOnChartArea: false
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: {
            display: true,
            text: 'Temperature (°C)'
          },
          grid: {
            drawOnChartArea: false
          }
        },
        y2: {
          type: 'linear',
          display: false,
          position: 'right',
          title: {
            display: true,
            text: 'CO₂ (ppm)'
          }
        }
      },
      plugins: {
        title: {
          display: true,
          text: room === 'all' ? 'All Rooms Data' : `${room} Data`,
          font: {
            size: 16
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              let label = context.dataset.label || '';
              if (label) label += ': ';
              label += context.parsed.y;
              return label;
            }
          }
        },
        legend: {
          position: 'top',
          labels: {
            boxWidth: 12,
            padding: 20,
            usePointStyle: true
          }
        }
      },
      animation: {
        duration: 1000,
        easing: 'easeOutQuart'
      }
    }
  });
}

// Update details table
function updateDetailsTable(data) {
  if (!elements.dataTableContainer) return;

  // Create table HTML
  const tableHTML = `
    <div class="chart-container">
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Room</th>
              <th>AQI</th>
              <th>Temp (°C)</th>
              <th>CO₂ (ppm)</th>
              <th>Humidity (%)</th>
              <th>TVOC (ppb)</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(d => `
              <tr>
                <td>${new Date(d.timestamp).toLocaleString()}</td>
                <td>${d.room}</td>
                <td style="color: ${aqiColor(aqiLevel(d.aqi))}">${d.aqi}</td>
                <td>${d.temperature}</td>
                <td>${d.co2}</td>
                <td>${d.humidity}</td>
                <td>${d.tvoc}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;

  elements.dataTableContainer.innerHTML = tableHTML;
}

// Show error message
function showError(message) {
  const errorElement = document.createElement('div');
  errorElement.className = 'error-message';
  errorElement.style.color = 'var(--danger)';
  errorElement.style.padding = '1rem';
  errorElement.style.textAlign = 'center';
  errorElement.textContent = message;
  
  if (elements.roomCards) {
    elements.roomCards.innerHTML = '';
    elements.roomCards.appendChild(errorElement);
  } else if (elements.dataTableContainer) {
    elements.dataTableContainer.innerHTML = '';
    elements.dataTableContainer.appendChild(errorElement);
  }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// Clean up when page is unloaded
window.addEventListener('beforeunload', () => {
  clearInterval(dataRefreshInterval);
  Object.values(chartInstances).forEach(chart => chart.destroy());
});