document.addEventListener('DOMContentLoaded', function() {
    // Get all filter headers
    const filterHeaders = document.querySelectorAll('.filter-header');
    
    // Add click event listener to each header
    filterHeaders.forEach(header => {
        header.addEventListener('click', function() {
            // Toggle active class on header
            this.classList.toggle('active');
            
            // Get the next sibling element (filter-content)
            const content = this.nextElementSibling;
            
            // Toggle show class on content
            if (content.classList.contains('filter-content')) {
                content.classList.toggle('show');
            }
        });
    });
});