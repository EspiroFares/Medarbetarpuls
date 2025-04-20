// Initialize the surveyChart
function initSurveyChart(chartID, chartLabels, chartData) {
    const surveyChartElement = document.getElementById(chartID);
    if (surveyChartElement) { // Check if the canvas exists, else the script will crash
        const ctx1 = surveyChartElement.getContext("2d");
        new Chart(ctx1, {
            type: "line",
            data: {
                labels: chartLabels,
                datasets: [{
                    label: "Answer Count",
                    data: chartData, // Example data
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
function initPieChart(chartID, chartLabels, chartData, chartColors) {
    const pieChart = document.getElementById(chartID);
    if (pieChart) { // Check if the canvas exists, else the script will crash
        const ctx2 = pieChart.getContext("2d");
        new Chart(ctx2, {
            type: "pie",
            data: {
                labels: chartLabels, // Example labels
                datasets: [{
                    label: "eNPS Responses",
                    data: chartData, // Example data
                    backgroundColor: chartColors,
                }]
            },
            options: {
                responsive: true
            }
        });
    } else {
        console.warn("pieChart canvas not found.");
    }
}

function initEnpsGauge(chartID, chartData, dataChange) {
    const enpsGaugeElement = document.getElementById(chartID);
    if (enpsGaugeElement) { // Check if the canvas exists, else the script will crash
        const ctx3 = enpsGaugeElement.getContext("2d");
        new Chart(ctx3, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: chartData, // Example data
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
                                content: ({chart}) => [ '↑' + dataChange,
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

function initEnpsBar(chartID, chartLabels, chartData){
    const enpsBarElement = document.getElementById(chartID);
    if (enpsBarElement) { // Check if the canvas exists, else the script will crash
        const ctx4 = enpsBarElement.getContext("2d");
        new Chart(ctx4, {
            type: 'bar',
            data: {
                labels: chartLabels,
                    datasets: [{
                        label: "eNPS Responses",
                        data: chartData, // Example data
                        backgroundColor: chartLabels.map((_, index) => {
                        if (index < 7) {
                            return '#EF4444'; // Red
                        } else if (index < 9) {
                            return '#FFB95A'; // Orange
                        } else {
                            return '#84CC16'; // Green
                        }
                        }),
                    }]
            },
            options: {
                responsive: true,
                borderRadius: 10,
                barThickness: 30,
                aspectRatio: 4,
                plugins: { // Add this section to control the legend
                    legend: {
                        display: false, // This will hide the legend
                    }
                },
                style: {
                    barPercentage: 'flex',
                    },
                scales: {
                    x: {
                        grid: {
                            display: false // Disable vertical grid lines
                        },
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

// Function to draw a gradient circle
function initAnswerFrequency(chartID, chartData, dataChange) {
    // Create a radial gradient
    const canvas = document.getElementById(chartID);
    const ctx = canvas.getContext('2d');

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radiusA = 60; 
    const radiusB = 110;

    const gradient = ctx.createRadialGradient(centerX, centerY, radiusA, centerX, centerY, radiusB);

    gradient.addColorStop(0, 'rgba(132, 204, 22, 1)'); // Full opacity at radius A (center)
    gradient.addColorStop(1, 'rgba(132, 204, 22, 0)'); // Transparent at radius B

    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw the circle with the gradient
    ctx.beginPath();
    ctx.arc(centerX, centerY, radiusB, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.closePath();
    ctx.font = "15px sans-serif";
    ctx.fillStyle = "black";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("↑ +" + dataChange, centerX, centerY - 20); 
    ctx.font = "30px sans-serif";
    ctx.fillText(chartData + "%", centerX, centerY + 10);
}