// Main JavaScript file for the IPM Admin Panel

// Toggle form visibility
function toggleForm(formId) {
    const form = document.getElementById(formId);
    if (form.style.display === 'none') {
        form.style.display = 'block';
    } else {
        form.style.display = 'none';
    }
}

// Confirm delete action
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

// Format currency
function formatCurrency(amount) {
    return '₹' + parseFloat(amount).toFixed(2);
}

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    // Add any initialization code here
    console.log('IPM Admin Panel initialized');
});
