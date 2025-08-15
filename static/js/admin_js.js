// This file contains JavaScript code for the admin dashboard charts 
const pieChart = new Chart(document.getElementById('pieChart'), {
    type: 'doughnut',
    data: {
        labels: ['Total Order', 'Customer Growth', 'Total Revenue'],
        datasets: [{
            data: [81, 22, 62],
            backgroundColor: ['#0d6efd', '#198754', '#ffc107']
        }]
    }
});

// Bar chart for top products
const lineChart = new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: {
        labels: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        datasets: [{
            label: 'Orders',
            data: [456, 480, 320, 600, 700, 500, 650],
            borderColor: '#0d6efd',
            fill: false
        }]
    }
});
// Bar chart for revenue
const revenueChart = new Chart(document.getElementById('revenueChart'), {
    type: 'line',
    data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{
            label: '2025',
            data: [30, 40, 35, 50, 45, 60],
            borderColor: '#dc3545',
            fill: false
        }]
    }
});

