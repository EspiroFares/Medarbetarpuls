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

function initEnpsGauge(chartID, chartData, dataChange, lastDateChange) {
    const enpsGaugeElement = document.getElementById(chartID);
    if (enpsGaugeElement) { // Check if the canvas exists, else the script will crash
        const ctx3 = enpsGaugeElement.getContext("2d");
        let dataChangeText = '';
        let chartDataText = '';
        let dataChangeColor = '';
        let chartDataColor = '';

        if (dataChange > 0) {
            dataChangeText = '↑' + dataChange;
            dataChangeColor = 'rgb(140, 214, 16)';
        } else if (dataChange < 0) {
            dataChangeText = '↓' + Math.abs(dataChange);
            dataChangeColor = 'rgb(214, 16, 16)';
        } else {
            dataChangeText = '+-0';
            dataChangeColor = 'black';
        }

        if (chartData > 0) {
            chartDataText = '+' + chartData; 
            if (chartData > 20) {
                chartDataColor = 'rgb(140, 214, 16)'; // Green
            } else {
                chartDataColor = 'rgb(248, 149, 28)'; // Orange
            }
        } else if (chartData < 0) {
            chartDataText = '-' + Math.abs(chartData);
            if (chartData < -20) {
                chartDataColor = 'rgb(214, 16, 16)'; // Red
            } else {
                chartDataColor = 'rgb(248, 149, 28)'; // Orange
            }
        } else {
            chartDataText = '0';
            chartDataColor = 'rgb(248, 149, 28)'; // Orange
        }
        
        new Chart(ctx3, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [100+chartData, 100-chartData],
                    backgroundColor: [chartDataColor, 'grey'],
                }],
            },
            options: {
                aspectRatio: 2,
                circumference: 180,
                rotation: -90,
                cutout: '80%',
                plugins: {
                    tooltip: {
                        enabled: false // Disable tooltips
                    },
                    annotation: {
                        annotations: {
                            doughnutLabel: {
                                type: 'doughnutLabel',
                                content: [dataChangeText,
                                  chartDataText,
                                  lastDateChange,
                                ],
                                drawTime: 'beforeDraw',
                                position: {
                                  y: '-30px'
                                },
                                font: [{size: 30, weight: 'bold'}, {size: 50, weight: 'bold'}, {size: 30}],
                                color: [dataChangeColor,chartDataColor,'black'],
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

function generateLabelContent(chartData, dataChange) {
    if (dataChange > 0) {
        return [
            '↑ ' + dataChange, // Up arrow with positive change
            '+' + chartData,    // Display chartData
            '2025/05/12',       // Date
        ];
    } else if (dataChange < 0) {
        return [
            '↓ ' + Math.abs(dataChange), // Down arrow with negative change
            '-' + chartData,              // Display chartData
            '2025/05/12',                  // Date
        ];
    } else {
        return [
            'No Change', // Indicate no change
            chartData,   // Display chartData
            '2025/05/12', // Date
        ];
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

    let colorStart;
    let colorEnd; 
    if (chartData < 40) {
        colorStart = 'rgb(204, 22, 22)'; // Red
        colorEnd = 'rgba(204, 22, 22, 0)';   // Transparent Red
    } else if (chartData < 60) {
        colorStart = 'rgb(248, 149, 28)'; // Orange
        colorEnd = 'rgba(248, 149, 28, 0)';   // Transparent Orange
    } else if (chartData < 80) {
        colorStart = 'rgb(252, 252, 29)'; // Yellow
        colorEnd = 'rgba(252, 252, 29, 0)';   // Transparent Yellow
    } else {
        colorStart = 'rgba(132, 204, 22, 1)'; // Green
        colorEnd = 'rgba(132, 204, 22, 0)';   // Transparent Green
    }

    const gradient = ctx.createRadialGradient(centerX, centerY, radiusA, centerX, centerY, radiusB);
    gradient.addColorStop(0, colorStart); // Full opacity at radius A (center)
    gradient.addColorStop(1, colorEnd);
    // Clear the canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw the circle with the gradient
    ctx.beginPath();
    ctx.arc(centerX, centerY, radiusB, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.closePath();
    ctx.font = "15px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    if (dataChange > 0) {
        ctx.fillStyle = "green"; // Change color to green if dataChange is positive
        ctx.fillText("↑ +" + dataChange + "%", centerX, centerY - 20);
    } else if (dataChange < 0) {
        ctx.fillStyle = "red"; // Change color to red if dataChange is negative
        ctx.fillText("↓ -" + dataChange + "%", centerX, centerY - 20);
    } else if (dataChange == 0) {
        ctx.fillStyle = "black"; // Default color
        ctx.fillText("+- " + dataChange + "%", centerX, centerY - 20);
    } 
    ctx.fillStyle = "black"
    ctx.font = "30px sans-serif";
    ctx.fillText(chartData + "%", centerX, centerY + 10);
}