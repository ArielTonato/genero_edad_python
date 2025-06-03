# Detector de Edad y Género con IA

Esta aplicación web utiliza inteligencia artificial para detectar la edad y el género de personas a partir de imágenes o mediante la cámara web en tiempo real.

## Características

- Detección de edad y género mediante DeepFace
- Subida de imágenes para análisis
- Captura y análisis en tiempo real con la cámara web
- Interfaz web intuitiva y responsive
- Algoritmos de filtrado para mejorar la precisión de las predicciones

## Requisitos

- Python 3.7 o superior
- Dependencias listadas en `requirements.txt`

## Instalación

1. Instala las dependencias:

```
pip install -r requirements.txt
```

2. Ejecuta la aplicación:

```
python app.py
```

3. Abre tu navegador y ve a `http://localhost:5000`

## Uso

### Subir Imagen

1. Haz clic en la pestaña "Subir Imagen"
2. Arrastra una imagen o haz clic para seleccionar una
3. Haz clic en "Analizar Imagen"
4. Visualiza los resultados de edad y género

### Usar Cámara

1. Haz clic en la pestaña "Usar Cámara"
2. Haz clic en "Iniciar Cámara"
3. La aplicación analizará automáticamente tu rostro cada pocos segundos
4. Haz clic en "Detener Cámara" cuando hayas terminado

## Cómo funciona

La aplicación utiliza DeepFace, una biblioteca de reconocimiento facial que implementa varios modelos de IA para detectar características faciales. Para mejorar la precisión:

- Aplica filtros para eliminar valores atípicos
- Utiliza la mediana en lugar de la media para calcular la edad
- Implementa suavizado exponencial para estabilizar las predicciones
- Utiliza un sistema de votación para determinar el género con mayor confianza
