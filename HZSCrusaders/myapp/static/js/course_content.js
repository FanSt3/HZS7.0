let currentVideoElement = null;

function toggleLesson(lessonId) {
    const lessonElement = document.querySelector(`[data-lesson-id="${lessonId}"]`);
    const wasActive = lessonElement.classList.contains('active');
    
    // Close all other lessons
    document.querySelectorAll('.lesson').forEach(l => l.classList.remove('active'));
    
    // Toggle current lesson
    if (!wasActive) {
        lessonElement.classList.add('active');
        // Play first video if available
        const firstVideo = lessonElement.querySelector('.video-item');
        if (firstVideo) {
            playVideo(firstVideo.dataset.videoUrl, firstVideo);
        }
    }
}

function playVideo(videoUrl, element) {
    if (!videoUrl) return;
    
    // Update video container
    const videoContainer = document.getElementById('video-container');
    videoContainer.innerHTML = `<iframe src="${videoUrl}" frameborder="0" allowfullscreen></iframe>`;
    videoContainer.style.display = 'block';
    
    // Update active state
    document.querySelectorAll('.video-item').forEach(v => v.classList.remove('active'));
    element.classList.add('active');
    
    // Update lesson content if needed
    const lessonElement = element.closest('.lesson');
    const title = lessonElement.querySelector('.lesson-title').textContent;
    const content = lessonElement.dataset.content;
    document.getElementById('lesson-title').textContent = title;
    document.getElementById('lesson-content').innerHTML = content;
} 