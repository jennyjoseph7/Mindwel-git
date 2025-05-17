// Handle mood selection in the mood tracker form
document.addEventListener('DOMContentLoaded', function() {
    const moodOptions = document.querySelectorAll('.mood-option');
    if (moodOptions) {
        moodOptions.forEach(option => {
            option.addEventListener('click', function() {
                // Remove selected class from all options
                moodOptions.forEach(opt => opt.classList.remove('selected'));
                // Add selected class to clicked option
                this.classList.add('selected');
                // Update hidden input value
                const moodInput = document.querySelector('input[name="mood_score"]');
                if (moodInput) {
                    moodInput.value = this.dataset.value;
                }
            });
        });
    }
});

// Auto-resize textarea
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });
});

// Smooth scrolling for chat container
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
});

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Add fade-in animation to elements
    var fadeElements = document.querySelectorAll('.card, .feature-card, .hero-section');
    fadeElements.forEach(function(element) {
        element.classList.add('fade-in');
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Mood selection animation
    var moodOptions = document.querySelectorAll('.mood-option');
    moodOptions.forEach(function(option) {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            moodOptions.forEach(function(opt) {
                opt.classList.remove('selected');
            });
            // Add selected class to clicked option
            this.classList.add('selected');
        });
    });

    // Auto-resize textareas
    var textareas = document.querySelectorAll('textarea');
    textareas.forEach(function(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });

    // Chat container scroll to bottom
    var chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Parallax effect for hero section
    var heroSection = document.querySelector('.hero-section');
    if (heroSection) {
        window.addEventListener('scroll', function() {
            var scrolled = window.pageYOffset;
            heroSection.style.backgroundPositionY = -(scrolled * 0.5) + 'px';
        });
    }

    // Initialize charts with nature theme colors
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = '#2D5A27';
        Chart.defaults.borderColor = '#9CAF88';
    }
});

// Form validation with nature-themed feedback
function validateForm(formId) {
    var form = document.getElementById(formId);
    if (!form) return true;

    var isValid = true;
    var inputs = form.querySelectorAll('input[required], textarea[required], select[required]');

    inputs.forEach(function(input) {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
            var feedback = input.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.textContent = 'This field is required';
            }
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Add loading animation to buttons
document.querySelectorAll('button[type="submit"]').forEach(function(button) {
    button.addEventListener('click', function() {
        if (this.form && validateForm(this.form.id)) {
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...';
        }
    });
});

// Add smooth transitions to all interactive elements
document.querySelectorAll('a, button, .mood-option, .emotion-tag').forEach(function(element) {
    element.style.transition = 'all 0.3s ease';
});

// Add hover effect to cards
document.querySelectorAll('.card').forEach(function(card) {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-5px)';
    });
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
}); 