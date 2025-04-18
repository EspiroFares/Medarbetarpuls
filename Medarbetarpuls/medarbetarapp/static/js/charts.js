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

function index(perc) {
    return perc < 70 ? 0 : perc < 90 ? 1 : 2;
  }

const COLORS = ['rgb(140, 214, 16)', 'rgb(239, 198, 0)', 'rgb(231, 24, 49)'];


  const data = {
    datasets: [{
      data: [33, 100 - 33],
      backgroundColor(ctx) {
        if (ctx.type !== 'data') {
          return;
        }
        if (ctx.index === 1) {
          return 'rgb(234, 234, 234)';
        }
        return 'rgb(140, 214, 16)';
      }
    }]
  };

function initEnpsGauge() {
    const enpsGaugeElement = document.getElementById("enpsGauge");
    if (enpsGaugeElement) { // Check if the canvas exists, else the script will crash
        const ctx3 = enpsGaugeElement.getContext("2d");
        new Chart(ctx3, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [70, 30], // Example data
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

const labels = ['0', '1', '2', '3', '4', '5', '6'];
const barData = {
  labels: labels,
  datasets: [{
    label: 'Survey Results',
    data: [65, 59, 80, 120, 56, 55, 40],
    backgroundColor: [
      'rgba(255, 99, 132, 0.2)',
      'rgba(255, 159, 64, 0.2)',
      'rgba(255, 205, 86, 0.2)',
      'rgba(75, 192, 192, 0.2)',
      'rgba(54, 162, 235, 0.2)',
      'rgba(153, 102, 255, 0.2)',
      'rgba(201, 203, 207, 0.2)'
    ],
    borderColor: [
      'rgb(255, 99, 132)',
      'rgb(255, 159, 64)',
      'rgb(255, 205, 86)',
      'rgb(75, 192, 192)',
      'rgb(54, 162, 235)',
      'rgb(153, 102, 255)',
      'rgb(201, 203, 207)'
    ],
    borderWidth: 2
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
                plugins: { // Add this section to control the legend
                    legend: {
                        display: false, // This will hide the legend
                    }
                },
                scales: {
                y: {
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