import cv2
import numpy as np
from deepface import DeepFace
from flask import Flask, render_template, request, Response, jsonify
import base64
import os
from statistics import median
import time
from datetime import datetime
from pykalman import KalmanFilter

app = Flask(__name__)

# Configurar para manejar correctamente caracteres especiales
app.config['JSON_AS_ASCII'] = False

# Crear directorio para guardar imágenes subidas si no existe
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Buffer para promediar predicciones de la cámara
predictions_buffer = []
# Aumentar el tamaño del buffer para mayor estabilidad
buffer_size = 30

# Inicializar filtro de Kalman con una secuencia válida de observaciones
kf = KalmanFilter(initial_state_mean=0, n_dim_obs=1)
observations = np.array([0, 0.1, 0.2])  # Secuencia inicial de observaciones
kf = kf.em(observations, n_iter=5)
state_mean, state_covariance = kf.filter_update(
    filtered_state_mean=np.array([0]),
    filtered_state_covariance=np.array([[1]])
)

def analyze_image(img):
    """Analiza una imagen para detectar edad y género"""
    try:
        # Mejorar contraste y brillo
        img_enhanced = cv2.convertScaleAbs(img, alpha=1.3, beta=30)

        # Analizar con DeepFace usando un backend más preciso
        result = DeepFace.analyze(
            img_enhanced, 
            actions=['age', 'gender'], 
            enforce_detection=True,  # Asegurar detección de rostros
            detector_backend='retinaface',  # Cambiar backend a 'mtcnn'
            silent=True
        )

        # Obtener predicciones
        age = result[0]['age']
        gender_probs = result[0]['gender']

        # Obtener el género con mayor probabilidad
        predicted_gender = max(gender_probs, key=gender_probs.get)
        confidence = gender_probs[predicted_gender]

        return {
            'success': True,
            'age': age,
            'gender': predicted_gender,
            'confidence': confidence,
            'gender_probs': gender_probs
        }
    except Exception as e:
        print(f"Error al analizar imagen: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def process_camera_frame(frame):
    """Procesa un frame de la cámara aplicando filtros y suavizado"""
    global predictions_buffer, state_mean, state_covariance

    # Analizar el frame
    result = analyze_image(frame)

    if not result['success']:
        return result

    # Agregar al buffer para suavizar predicciones
    predictions_buffer.append({
        'age': result['age'],
        'gender': result['gender'],
        'confidence': result['confidence']
    })

    # Mantener solo las últimas predicciones
    if len(predictions_buffer) > buffer_size:
        predictions_buffer.pop(0)

    # Calcular promedios y aplicar filtros
    if len(predictions_buffer) >= 5:  # Esperar al menos 5 predicciones
        # Filtrar valores atípicos de edad usando el método IQR
        ages = [p['age'] for p in predictions_buffer]
        ages.sort()

        # Calcular cuartiles
        q1_index = len(ages) // 4
        q3_index = 3 * len(ages) // 4
        q1 = ages[q1_index]
        q3 = ages[q3_index]
        iqr = q3 - q1

        # Definir límites para filtrar valores atípicos
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Filtrar edades dentro de los límites
        filtered_ages = [age for age in ages if lower_bound <= age <= upper_bound]

        # Si después de filtrar quedan suficientes valores, usar la mediana
        if len(filtered_ages) >= 3:
            avg_age = median(filtered_ages)  # La mediana es más robusta que la media
        else:
            # Si no hay suficientes valores después de filtrar, usar todos con la mediana
            avg_age = median(ages)

        # Aplicar filtro de Kalman para suavizar la edad
        state_mean, state_covariance = kf.filter_update(
            filtered_state_mean=state_mean,
            filtered_state_covariance=state_covariance,
            observation=np.array([avg_age])
        )
        smoothed_age = state_mean[0]

        # Determinar género más frecuente
        gender_votes = {}
        for p in predictions_buffer:
            if p['confidence'] > 70:  # Solo considerar predicciones con alta confianza
                gender_votes[p['gender']] = gender_votes.get(p['gender'], 0) + 1

        if gender_votes:
            final_gender = max(gender_votes, key=gender_votes.get)
            # Calcular porcentaje de confianza para el género final
            total_votes = sum(gender_votes.values())
            gender_confidence = (gender_votes[final_gender] / total_votes) * 100
        else:
            final_gender = result['gender']
            gender_confidence = result['confidence']

        return {
            'success': True,
            'age': int(smoothed_age),
            'gender': final_gender,
            'confidence': gender_confidence,
            'gender_probs': result['gender_probs']
        }
    else:
        # No hay suficientes datos para filtrar, devolver el resultado actual
        return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se encontró archivo'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó archivo'})
    
    # Guardar archivo con timestamp para evitar colisiones
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Leer la imagen y analizarla
    img = cv2.imread(filepath)
    if img is None:
        return jsonify({'success': False, 'error': 'No se pudo leer la imagen'})
    
    # Analizar la imagen
    result = analyze_image(img)
    
    if result['success']:
        # Dibujar resultados en la imagen
        text = f"Edad: {int(result['age'])} - Genero: {result['gender']} ({result['confidence']:.1f}%)"
        cv2.putText(img, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Guardar imagen con resultados
        result_filename = f"result_{filename}"
        result_filepath = os.path.join(UPLOAD_FOLDER, result_filename)
        cv2.imwrite(result_filepath, img)
        
        # Devolver resultado y ruta de la imagen procesada
        return jsonify({
            'success': True,
            'age': int(result['age']),
            'gender': result['gender'],
            'confidence': result['confidence'],
            'image_url': f"/static/uploads/{result_filename}"
        })
    else:
        return jsonify(result)

@app.route('/analyze_camera', methods=['POST'])
def analyze_camera():
    # Recibir imagen de la cámara en base64
    data = request.get_json()
    
    # Verificar si existe alguno de los dos posibles nombres de parámetro
    if not data:
        return jsonify({'success': False, 'error': 'No se recibieron datos'})
    
    # Buscar la imagen en cualquiera de los dos posibles parámetros
    if 'image' in data:
        image_b64 = data['image']
    elif 'image_data' in data:
        image_b64 = data['image_data']
    else:
        return jsonify({'success': False, 'error': 'No se recibió imagen'})
    
    # Decodificar imagen base64
    try:
        # Eliminar el prefijo 'data:image/jpeg;base64,' si existe
        if 'base64,' in image_b64:
            image_b64 = image_b64.split('base64,')[1]
        
        # Decodificar y convertir a imagen OpenCV
        img_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'success': False, 'error': 'No se pudo decodificar la imagen'})
        
        # Procesar el frame de la cámara
        result = process_camera_frame(img)
        
        return jsonify(result)
    except Exception as e:
        print(f"Error al procesar imagen de cámara: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
