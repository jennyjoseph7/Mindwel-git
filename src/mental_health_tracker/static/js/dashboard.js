// Dashboard Initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mood chart
    initMoodChart();
    
    // Setup refresh tips button
    setupRefreshTips();
    
    // Apply animations to elements
    applyAnimations();
    
    // Update current date
    updateCurrentDate();
});

// Initialize Mood Chart
function initMoodChart() {
    const ctx = document.getElementById('moodChart');
    
    if (!ctx) return;
    
    const moodData = {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
            {
                label: 'Mood Level',
                data: [65, 59, 80, 81, 75, 85, 78],
                fill: true,
                backgroundColor: 'rgba(139, 195, 74, 0.2)',
                borderColor: '#8bc34a',
                tension: 0.4,
                pointBackgroundColor: '#4caf50',
                pointBorderColor: '#fff',
                pointRadius: 5,
                pointHoverRadius: 7
            }
        ]
    };
    
    const config = {
        type: 'line',
        data: moodData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            if (value === 0) return 'Low';
                            if (value === 50) return 'Neutral';
                            if (value === 100) return 'High';
                            return '';
                        }
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.15)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(200, 200, 200, 0.15)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(76, 175, 80, 0.8)',
                    titleFont: {
                        size: 14
                    },
                    bodyFont: {
                        size: 13
                    },
                    callbacks: {
                        label: function(context) {
                            let label = '';
                            const value = context.parsed.y;
                            
                            if (value >= 80) label = 'Very Positive';
                            else if (value >= 65) label = 'Positive';
                            else if (value >= 45) label = 'Neutral';
                            else if (value >= 30) label = 'Low';
                            else label = 'Very Low';
                            
                            return `Mood: ${label} (${value}%)`;
                        }
                    }
                }
            }
        }
    };
    
    // Create the chart
    new Chart(ctx, config);
}

// Setup refresh tips button
function setupRefreshTips() {
    const refreshBtn = document.getElementById('refresh-tips');
    
    if (!refreshBtn) return;
    
    const tips = [
        {
            icon: 'seedling',
            title: 'Forest Bathing',
            text: 'Spend 20 minutes under trees to reduce stress hormones'
        },
        {
            icon: 'water',
            title: 'Water Sounds',
            text: 'Listen to flowing water to activate your parasympathetic nervous system'
        },
        {
            icon: 'cloud-sun',
            title: 'Morning Light',
            text: 'Get 10 minutes of morning sunlight to regulate your circadian rhythm'
        },
        {
            icon: 'wind',
            title: 'Deep Breathing',
            text: 'Practice 4-7-8 breathing to calm your nervous system'
        },
        {
            icon: 'leaf',
            title: 'Plant Therapy',
            text: 'Care for indoor plants to improve focus and air quality'
        },
        {
            icon: 'moon',
            title: 'Nature Sleep',
            text: 'Use nature sounds for better sleep quality and relaxation'
        },
        {
            icon: 'tree',
            title: 'Grounding Practice',
            text: 'Walk barefoot on grass for 5 minutes to reduce inflammation'
        },
        {
            icon: 'umbrella-beach',
            title: 'Blue Space',
            text: 'Spend time near water to boost your mood and creativity'
        },
        {
            icon: 'mountain',
            title: 'Green Exercise',
            text: 'Exercise outdoors for greater mental health benefits'
        }
    ];
    
    refreshBtn.addEventListener('click', function() {
        const tipsList = document.querySelector('.tips-list');
        const tipItems = tipsList.querySelectorAll('.tip-item');
        
        // Get current tips
        const currentTips = [];
        tipItems.forEach(item => {
            const title = item.querySelector('h5').textContent;
            currentTips.push(title);
        });
        
        // Filter out current tips
        const availableTips = tips.filter(tip => !currentTips.includes(tip.title));
        
        // If we've used all tips, reset
        if (availableTips.length < 3) {
            refreshBtn.click(); // recursive call to reset
            return;
        }
        
        // Select 3 random tips
        const selectedTips = [];
        for (let i = 0; i < 3; i++) {
            const randomIndex = Math.floor(Math.random() * availableTips.length);
            selectedTips.push(availableTips[randomIndex]);
            availableTips.splice(randomIndex, 1);
        }
        
        // Update DOM with new tips
        tipItems.forEach((item, index) => {
            const tip = selectedTips[index];
            const icon = item.querySelector('.tip-icon i');
            const title = item.querySelector('h5');
            const text = item.querySelector('p');
            
            // Add fade out class
            item.classList.add('fade-out');
            
            // After animation completes, update content and fade back in
            setTimeout(() => {
                icon.className = `fas fa-${tip.icon}`;
                title.textContent = tip.title;
                text.textContent = tip.text;
                
                // Remove fade out and add fade in
                item.classList.remove('fade-out');
                item.classList.add('fade-in');
                
                // Remove fade in after animation completes
                setTimeout(() => {
                    item.classList.remove('fade-in');
                }, 500);
            }, 500);
        });
        
        // Button animation
        refreshBtn.classList.add('rotate-animation');
        setTimeout(() => {
            refreshBtn.classList.remove('rotate-animation');
        }, 500);
    });
}

// Apply animations to elements
function applyAnimations() {
    // Add fade-in animation to glass cards
    const glassCards = document.querySelectorAll('.glass-card');
    glassCards.forEach((card, index) => {
        card.style.animationDelay = `${0.1 * index}s`;
        card.classList.add('fade-in-up');
    });
    
    // Add hover effect to action cards
    const actionCards = document.querySelectorAll('.action-card, .resource-card');
    actionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            const overlay = this.querySelector('.nature-bg');
            overlay.classList.add('scale-bg');
        });
        
        card.addEventListener('mouseleave', function() {
            const overlay = this.querySelector('.nature-bg');
            overlay.classList.remove('scale-bg');
        });
    });
}

// Update current date
function updateCurrentDate() {
    const dateElement = document.querySelector('.welcome-text');
    
    if (!dateElement) return;
    
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const formattedDate = now.toLocaleDateString('en-US', options);
    
    // Update the date in the welcome text
    dateElement.innerHTML = `Today is <span class="highlight-text">${formattedDate}</span>`;
}

// Add CSS animations
document.head.insertAdjacentHTML('beforeend', `
<style>
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes rotate {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    
    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }
    
    .fade-in-up {
        animation: fadeInUp 0.6s ease-out forwards;
        opacity: 0;
    }
    
    .rotate-animation {
        animation: rotate 0.5s ease-in-out;
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out forwards;
    }
    
    .fade-out {
        animation: fadeOut 0.5s ease-out forwards;
    }
    
    .scale-bg {
        transform: scale(1.1) !important;
        opacity: 0.25 !important;
    }
</style>
`);
