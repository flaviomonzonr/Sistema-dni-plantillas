# 🇵🇪 EscanDNI Perú - Sistema Web de Escaneo y Extracción de Documentos de Identidad

Sistema web de nivel producción diseñado para escanear, preprocesar con **OpenCV**, extraer datos mediante **OCR (Tesseract / Cloud Vision)** y almacenar automáticamente la información en **SQLite** y un archivo **Excel incremental (`Registros.xlsx`)** de documentos de identidad peruanos (**DNI Azul**, **DNI Electrónico** y **Carnet de Extranjería**, ambas caras).

---

## 🚀 Características Principales

1. **Captura Dual Flexible**:
   - Subida de archivos (PNG, JPG, WebP) mediante drag-and-drop.
   - Captura en tiempo real con cámara web o cámara de celular con selector de cámara frontal/trasera y cuadrícula guía de tarjeta ID-1.
2. **Pipeline de Preprocesamiento OpenCV (8 Fases)**:
   - Corrección de perspectiva y recorte automático de bordes (Aspect Ratio ~1.586).
   - Conversión a escala de grises.
   - Reducción de ruido avanzada (`fastNlMeansDenoising` / `bilateralFilter`).
   - Realce de nitidez con filtro Unsharp Masking y kernel de realce.
   - Ajuste adaptativo de brillo y contraste (CLAHE).
   - Binarización adaptativa (Gaussian C + Otsu).
   - Detección automática de borrosidad mediante la **Varianza del Laplaciano** con alertas proactivas para el usuario en caso de baja calidad.
   - Almacenamiento dual de imagen original y procesada para auditoría.
3. **Extracción y Validación OCR Tolerante a Variaciones**:
   - Extracción de **DNI (Anverso y Reverso)**: Apellidos, Nombres, Número de DNI (8 dígitos), Sexo, Fecha de Nacimiento, Dirección, Ubigeo, Fechas de Emisión/Caducidad, Grupo Sanguíneo, Estado Civil.
   - Soporte para **MRZ (Machine Readable Zone ICAO TD1)** en DNI electrónico para validación cruzada con 99% de confianza.
   - Extracción de **Carnet de Extranjería**: Apellidos y Nombres, N° Carné (9 dígitos/alfanumérico), Nacionalidad, Calidad Migratoria, Fechas de Emisión/Vencimiento, Dirección.
   - Cálculo de porcentaje de confianza por campo (Verde ≥80%, Amarillo 50-79%, Rojo <50%).
4. **Vista Previa Editable con Validación en Tiempo Real**:
   - Edición manual de cualquier campo antes de confirmar.
   - Comparador visual de imagen Original vs Mejorada con OpenCV.
5. **Persistencia Dual (SQLite + Excel Incremental)**:
   - Base de datos relacional SQLite (`data/records.db`).
   - Archivo Excel maestro estilizado (`exports/Registros.xlsx`) que se actualiza fila por fila automáticamente con `openpyxl`.
6. **Módulo de Historial y Exportación**:
   - Tabla de registros con búsqueda por documento/nombre y filtros por fecha y tipo.
   - Descarga directa del archivo Excel maestro o exportación personalizada filtrada.
   - Modal de detalle para visualizar las imágenes asociadas (original y mejorada).

---

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.10+ con **FastAPI**, **Uvicorn**, **Pydantic v2**, **SQLAlchemy**
- **Procesamiento de Imagen**: **OpenCV** (`opencv-python`), **NumPy**
- **Motor OCR**: **Tesseract OCR** (`pytesseract`) con arquitectura modular preparada para **Google Cloud Vision** y **AWS Textract**
- **Exportación Excel**: **openpyxl**
- **Frontend**: **React 19**, **Vite**, **TailwindCSS**, **Lucide Icons**, **Axios**, **Canvas-Confetti**

---

## 📦 Instalación y Requisitos Previos

### 1. Instalar Tesseract OCR en Windows
Tesseract es el motor OCR de código abierto utilizado para la lectura de texto local:

**Opción A (Recomendada con Winget):**
Abre una terminal PowerShell o CMD y ejecuta:
```powershell
winget install UB-Mannheim.TesseractOCR
```

**Opción B (Instalador manual):**
1. Descarga el instalador de 64 bits desde: [UB-Mannheim Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki)
2. Instálalo en la ruta por defecto (`C:\Program Files\Tesseract-OCR`).
3. *(Opcional)* Si instalaste Tesseract en una ruta personalizada, configura la variable de entorno:
   ```powershell
   $env:TESSERACT_PATH = "C:\TuRuta\tesseract.exe"
   ```

---

### 2. Instalación de Dependencias del Backend

Abre una terminal en la raíz del proyecto:
```powershell
# Instalar paquetes requeridos
python -m pip install -r backend/requirements.txt
```

---

### 3. Instalación de Dependencias del Frontend

En la misma carpeta o en otra terminal:
```powershell
cd frontend
npm install
cd ..
```

---

## 🏃‍♂️ Cómo Ejecutar el Sistema

### Paso 1: Iniciar el Servidor Backend (FastAPI)
Desde la raíz del proyecto:
```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
El backend estará disponible en: `http://localhost:8000`  
Documentación Swagger interactiva: `http://localhost:8000/docs`

### Paso 2: Iniciar el Frontend (React + Vite)
En otra terminal, dentro de la carpeta `frontend/`:
```powershell
cd frontend
npm run dev
```
La aplicación web se abrirá en: `http://localhost:5173`

---

## 📂 Estructura del Código

```
Escaneo de DNI/
├── backend/
│   ├── main.py                  # API FastAPI, rutas REST y static uploads
│   ├── config.py                # Rutas, umbrales de nitidez y auto-detección de Tesseract
│   ├── database.py              # Modelos SQLite y sesiones SQLAlchemy
│   ├── schemas.py               # Modelos Pydantic para escaneo, registros y respuestas
│   ├── image_processing/
│   │   ├── perspective.py       # Detección de contornos ID-1 y corrección de perspectiva
│   │   └── pipeline.py          # Pipeline de 8 pasos OpenCV (denoise, CLAHE, Laplaciano)
│   ├── ocr/
│   │   ├── base.py              # Interfaz BaseOCREngine y dataclasses de palabras/líneas
│   │   ├── tesseract_engine.py  # Motor Tesseract con multi-PSM y parser MRZ
│   │   ├── cloud_vision.py      # Adaptador preparado para Google Cloud Vision API
│   │   └── textract.py          # Adaptador preparado para AWS Textract
│   ├── extractors/
│   │   ├── dni_extractor.py     # Parser inteligente de DNI Azul y DNIe con MRZ TD1
│   │   ├── ce_extractor.py      # Parser de Carnet de Extranjería
│   │   └── validators.py        # Validadores de 8 dígitos, fechas calendario y regiones
│   ├── storage/
│   │   ├── excel_manager.py     # Módulo openpyxl con inserción incremental
│   │   └── file_manager.py      # Gestión de guardado de imágenes
│   ├── tests/                   # Suite de pruebas unitarias
│   └── requirements.txt         # Dependencias Python
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx           # Barra superior con estado del sistema
│   │   │   ├── CaptureZone.jsx      # Selector, dropzones, cámara y demo loader
│   │   │   ├── CameraModal.jsx      # Cámara en vivo con guía visual de carnet
│   │   │   ├── ImageCompare.jsx     # Comparador de imagen original vs OpenCV mejorada
│   │   │   ├── ReviewForm.jsx       # Formulario con barras de confianza e inserción
│   │   │   ├── HistoryView.jsx      # Tabla de registros, búsqueda y exportación
│   │   │   └── RecordDetailModal.jsx# Modal de detalle con visor de fotos
│   │   ├── services/api.js          # Cliente HTTP Axios
│   │   ├── App.jsx                  # Coordinador de vistas y estado global
│   │   └── index.css                # Estilos Tailwind y glassmorphism
│   ├── package.json
│   └── vite.config.js
├── uploads/                     # Almacenamiento de imágenes originales y procesadas
├── exports/                     # Archivo maestro Registros.xlsx
└── README.md
```

---

## 🧪 Ejecutar Pruebas Automatizadas

Para validar los módulos de validación, pipeline OpenCV, extractores de DNI/CE y Excel:
```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
```

---

## 📊 Hoja Excel de Salida

El sistema genera y actualiza automáticamente el archivo `exports/Registros.xlsx` con la siguiente estructura de columnas estilizadas:
1. `Fecha de escaneo`
2. `Tipo de documento`
3. `Apellido Paterno`
4. `Apellido Materno`
5. `Nombres`
6. `Número de documento`
7. `Nacionalidad`
8. `Fecha de Nacimiento`
9. `Sexo`
10. `Dirección`
11. `Fecha de Emisión`
12. `Fecha de Vencimiento`
13. `Observaciones`
