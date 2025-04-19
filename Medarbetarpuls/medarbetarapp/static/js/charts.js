// Initialize the surveyChart
function initSurveyChart() {
    const surveyChartElement = document.getElementById("surveyChart");
    if (surveyChartElement) { // Check if the canvas exists, else the script will crash
        const ctx1 = surveyChartElement.getContext("2d");
        new Chart(ctx1, {
            type: "line",
            data: {
                labels: ["Label 1", "Label 2"], // Example labels
                datasets: [{
                    label: "Answer Count",
                    data: [10, 20], // Example data
                    backgroundColor: "rgba(54, 162, 235, 0.5)",
                    borderColor: "rgba(54, 162, 235, 1)",
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } else {
        console.warn("surveyChart canvas not found.");
    }
}

// Initialize the enpsChart
function initEnpsChart() {
    const enpsChartElement = document.getElementById("enpsChart");
    if (enpsChartElement) { // Check if the canvas exists, else the script will crash
        const ctx2 = enpsChartElement.getContext("2d");
        new Chart(ctx2, {
            type: "pie",
            data: {
                labels: ["Happy", "Neutral", "Sad"], // Example labels
                datasets: [{
                    label: "eNPS Responses",
                    data: [3, 2, 1], // Example data
                    backgroundColor: [
                        "rgba(75, 192, 192, 0.5)",
                        "rgba(255, 206, 86, 0.5)",
                        "rgba(255, 99, 132, 0.5)"
                    ],
                    borderColor: [
                        "rgba(75, 192, 192, 1)",
                        "rgba(255, 206, 86, 1)",
                        "rgba(255, 99, 132, 1)"
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true
            }
        });
    } else {
        console.warn("enpsChart canvas not found.");
    }
}

function initEnpsGauge() {
    const enpsGaugeElement = document.getElementById("enpsGauge");
    if (enpsGaugeElement) { // Check if the canvas exists, else the script will crash
        const ctx3 = enpsGaugeElement.getContext("2d");
        new Chart(ctx3, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [-70, 100-70], // Example data
                    backgroundColor: ['rgb(140, 214, 16)', 'grey'],
                }],
            },
            options: {
                aspectRatio: 2,
                circumference: 180,
                rotation: -90,
                cutout: '80%',
                plugins: {
                    annotation: {
                        annotations: {
                            doughnutLabel: {
                                type: 'doughnutLabel',
                                content: ({chart}) => [ '↑ 10',
                                  '+' + chart.data.datasets[0].data[0].toFixed(0),
                                  '2025/05/12',
                                ],
                                drawTime: 'beforeDraw',
                                position: {
                                  y: '-30px'
                                },
                                font: [{size: 30}, {size: 50, weight: 'bold'}, {size: 30}],
                                color: ({chart}) => ['rgb(140, 214, 16)','rgb(140, 214, 16)', 'grey']
                              }
                        }
                    }
                }
              }
        });
    } else {
        console.warn("enpsGauge canvas not found.");
    }
}

const labels = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];

const barData = {
  labels: labels,
  datasets: [{
    label: 'Survey name',
    data: [65, 59, 80, 30, 56, 55, 40, 20, 10, 5, 10], // Example data
    backgroundColor: labels.map((_, index) => {
      if (index < 2) {
        return '#EF4444'; // Red
      } else if (index < 9) {
        return '#FFB95A'; // Orange
      } else {
        return '#84CC16'; // Green
      }
    }),
  }]
};

function initEnpsBar(){
    const enpsBarElement = document.getElementById("enpsBar");
    if (enpsBarElement) { // Check if the canvas exists, else the script will crash
        const ctx4 = enpsBarElement.getContext("2d");
        new Chart(ctx4, {
            type: 'bar',
            data: barData,
            options: {
                responsive: true,
                borderRadius: 10,
                plugins: { // Add this section to control the legend
                    legend: {
                        display: false, // This will hide the legend
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false // Disable vertical grid lines
                        }
                    },
                y: {
                    border: {
                        dash: [5, 5] // Make vertical grid lines dashed
                    },
                    beginAtZero: true
                }
                }
            },
        });
    } else {
        console.warn("enpsBar canvas not found.");
    }
}


// Initialize charts
document.addEventListener("DOMContentLoaded", function() {
    initSurveyChart();
    initEnpsChart();
    initEnpsGauge();
    initEnpsBar();
});