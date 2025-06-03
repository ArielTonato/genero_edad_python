document.addEventListener('DOMContentLoaded', function() {
    // Referencias a elementos del DOM
    const uploadTab = document.getElementById('upload-tab');
    const cameraTab = document.getElementById('camera-tab');
    const uploadContent = document.getElementById('upload-content');
    const cameraContent = document.getElementById('camera-content');
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resultsContainer = document.getElementById('results-container');
    const resultImage = document.getElementById('result-image');
    const ageResult = document.getElementById('age-result');
    const genderResult = document.getElementById('gender-result');
    const confidenceResult = document.getElementById('confidence-result');
    const backBtn = document.getElementById('back-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const startCameraBtn = document.getElementById('start-camera');
    const stopCameraBtn = document.getElementById('stop-camera');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    
    let stream = null;
    let cameraActive = false;
    let cameraAnalysisInterval = null;
    
    // Cambio entre pestañas
    uploadTab.addEventListener('click', function() {
        uploadTab.classList.add('active');
        cameraTab.classList.remove('active');
        uploadContent.classList.remove('hidden');
        cameraContent.classList.add('hidden');
        resultsContainer.classList.add('hidden');
        stopCamera();
    });
    
    cameraTab.addEventListener('click', function() {
        cameraTab.classList.add('active');
        uploadTab.classList.remove('active');
        cameraContent.classList.remove('hidden');
        uploadContent.classList.add('hidden');
        resultsContainer.classList.add('hidden');
    });
    
    // Funcionalidad de arrastrar y soltar
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    // Manejar archivos subidos por el usuario
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            previewFile(this.files[0]);
        }
    });
    
    // Manejar archivos arrastrados al área de subida
    dropArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('highlight');
    });
    
    dropArea.addEventListener('dragleave', function() {
        this.classList.remove('highlight');
    });
    
    dropArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('highlight');
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileInput.files = e.dataTransfer.files;
            previewFile(e.dataTransfer.files[0]);
        }
    });
    
    // Abrir selector de archivos al hacer clic en el área de subida
    dropArea.addEventListener('click', function() {
        fileInput.click();
    });
    
    function previewFile(file) {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onloadend = function() {
            previewImage.src = reader.result;
            previewContainer.style.display = 'block';
            document.querySelector('.upload-prompt').style.display = 'none';
        };
    }
    
    // Analizar imagen subida
    analyzeBtn.addEventListener('click', function() {
        if (previewImage.src) {
            // Mostrar overlay de carga
            loadingOverlay.classList.add('active');
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Ocultar overlay de carga
                loadingOverlay.classList.remove('active');
                
                if (data.success) {
                    showResults(data);
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                // Ocultar overlay de carga en caso de error
                loadingOverlay.classList.remove('active');
                alert('Error al procesar la imagen: ' + error);
            });
        }
    });
    
    // Mostrar resultados
    function showResults(data) {
        // Ocultar contenido de pestañas
        uploadContent.classList.add('hidden');
        cameraContent.classList.add('hidden');
        
        // Mostrar resultados
        resultsContainer.classList.remove('hidden');
        
        // Actualizar imagen de resultado
        resultImage.src = data.image_url;
        
        // Actualizar valores
        ageResult.textContent = data.age;
        genderResult.textContent = data.gender;
        confidenceResult.textContent = data.confidence + '%';
    }
    
    // Volver al inicio
    backBtn.addEventListener('click', function() {
        resultsContainer.classList.add('hidden');
        
        if (uploadTab.classList.contains('active')) {
            uploadContent.classList.remove('hidden');
        } else {
            cameraContent.classList.remove('hidden');
        }
    });
    
    // Funcionalidad de cámara
    startCameraBtn.addEventListener('click', startCamera);
    stopCameraBtn.addEventListener('click', stopCamera);
    
    function startCamera() {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then(function(mediaStream) {
                stream = mediaStream;
                video.srcObject = mediaStream;
                video.play();
                startCameraBtn.disabled = true;
                stopCameraBtn.disabled = false;
                
                // Iniciar análisis periódico
                cameraInterval = setInterval(analyzeVideoFrame, 1000);
            })
            .catch(function(error) {
                console.error('Error al acceder a la cámara: ', error);
                alert('No se pudo acceder a la cámara. Asegúrate de dar permisos.');
            });
    }
    
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            video.srcObject = null;
            startCameraBtn.disabled = false;
            stopCameraBtn.disabled = true;
            
            // Detener análisis periódico
            clearInterval(cameraInterval);
        }
    }
    
    // Analizar frame de video
    function analyzeVideoFrame() {
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
            // Dibujar frame en el canvas
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Convertir a base64
            const imageData = canvas.toDataURL('image/jpeg');
            
            // Enviar al servidor para análisis
            fetch('/analyze_camera', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image: imageData })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateCameraResults(data);
                }
            })
            .catch(error => {
                console.error('Error al analizar frame: ', error);
            });
        }
    }
    
    function updateCameraResults(data) {
        // Mostrar resultados sobre el video
        const overlay = document.createElement('div');
        overlay.className = 'camera-overlay';
        overlay.innerHTML = `
            <div class="camera-results">
                <p>Edad: ${data.age}</p>
                <p>Género: ${data.gender}</p>
                <p>Confianza: ${data.confidence.toFixed(1)}%</p>
            </div>
        `;
        
        // Eliminar overlay anterior si existe
        const oldOverlay = document.querySelector('.camera-overlay');
        if (oldOverlay) {
            oldOverlay.remove();
        }
        
        // Agregar nuevo overlay
        video.parentNode.appendChild(overlay);
    }
});
