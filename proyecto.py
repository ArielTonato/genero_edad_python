import cv2
from deepface import DeepFace
import numpy as np
from collections import deque
from statistics import median, mean

# Abre la cámara
cap = cv2.VideoCapture(0)

print("Presiona 'q' para salir...")

# Buffer para promediar predicciones
predictions_buffer = []
buffer_size = 15  # Aumentado para mejor estabilidad

while True:
    ret, frame = cap.read()
    if not ret:
        break

    try:
        # Mejora la calidad del frame
        # Voltear horizontalmente para efecto espejo
        frame = cv2.flip(frame, 1)
        
        # Mejorar contraste y brillo
        frame_enhanced = cv2.convertScaleAbs(frame, alpha=1.2, beta=20)
        
        # Analiza el frame con DeepFace
        result = DeepFace.analyze(
            frame_enhanced, 
            actions=['age', 'gender'], 
            enforce_detection=False,
            detector_backend='opencv',
            silent=True  # Reducir mensajes en consola
        )

        # Obtener predicciones
        age = result[0]['age']
        gender_probs = result[0]['gender']
        
        # Obtener el género con mayor probabilidad
        predicted_gender = max(gender_probs, key=gender_probs.get)
        confidence = gender_probs[predicted_gender]
        
        # Agregar al buffer para suavizar predicciones
        predictions_buffer.append({
            'age': age,
            'gender': predicted_gender,
            'confidence': confidence
        })
        
        # Mantener solo las últimas predicciones
        if len(predictions_buffer) > buffer_size:
            predictions_buffer.pop(0)
        
        # Calcular promedios y aplicar filtros
        if len(predictions_buffer) >= 5:  # Esperar al menos 5 predicciones
            # Filtrar valores atípicos de edad usando el método IQR (Rango Intercuartil)
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
            
            # Aplicar suavizado exponencial (dar más peso a las predicciones recientes)
            alpha = 0.3  # Factor de suavizado (0-1): mayor valor da más peso a predicciones recientes
            current_age = ages[-1]  # La predicción más reciente
            smoothed_age = alpha * current_age + (1 - alpha) * avg_age
            
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
                final_gender = predicted_gender
                gender_confidence = confidence
            
            text = f"Edad: {int(smoothed_age)} - Genero: {final_gender} ({gender_confidence:.1f}%)"
        else:
            text = "Analizando..."

        # Mostrar resultados en el frame
        cv2.putText(frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Mostrar información adicional de confianza
        confidence_text = f"Confianza: M={gender_probs.get('Man', 0):.1f}% F={gender_probs.get('Woman', 0):.1f}%"
        cv2.putText(frame, confidence_text, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
    except Exception as e:
        print("Error al analizar:", e)
        cv2.putText(frame, "Error en deteccion", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Mostrar el frame con predicciones
    cv2.imshow('Prediccion de Edad y Genero', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cierra la cámara
cap.release()
cv2.destroyAllWindows()