# NFCito Studio — Aplicación de Escritorio para Mini Álbumes y Llaveros NFC

**NFCito Studio** es una aplicación de escritorio nativa para Windows diseñada para emprendedores y creadores de llaveros con mini estuches de CD transparentes (acrílicos) y etiquetas NFC.

Permite diseñar cada una de las piezas gráficas con tolerancias milimétricas exactas, organizarlas de manera eficiente en hojas de papel (A4, Carta, etc.) y exportarlas en documentos PDF listos para imprimir a escala 100% real.

---

## 🚀 Características Principales

### 1. Dos Modos de Trabajo
- **Modo Manual (Diseñador de Álbum):**
  - Diseña independientemente: **Portada frontal**, **Lomo o bordes laterales**, **Contraportada**, **Etiqueta circular del CD**, e **Interior / libreto**.
  - Permite importar imágenes individuales, desplazarlas con arrastre de ratón (*pan*), ampliar/reducir (*zoom* con rueda) y rotar (0°, 90°, 180°, 270°).
  - Conserva estrictamente las proporciones originales evitando deformaciones de imagen (*cover* proporcional).
  - **Previsualización de corte en tiempo real:** muestra la foto completa con una máscara translúcida oscura exterior para ver con exactitud qué se corta y qué queda dentro de la pieza.
  - **Encuadre ultra-fluido (60 FPS):** arrastre de imagen con el ratón directamente sobre el lienzo para acomodar el encuadre en vivo, con zoom mediante la rueda del ratón.
  - Activa o desactiva la impresión de piezas específicas.
  - **Editor Tipográfico Avanzado (Contraportada):**
    - Selección de fuentes del sistema (Arial, Calibri, Segoe UI, Impact, Times New Roman, Georgia, Verdana, Tahoma, Bahnschrift, Courier New).
    - Botones de estilo: **Negrita (Bold)** y *Cursiva (Italic)*.
    - Control de tamaño de fuente independiente para el título y el cuerpo del texto / canciones.
    - Alineación horizontal (Izquierda, Centro, Derecha) y vertical (Arriba, Centro, Abajo).
    - Color de texto con selector visual y paleta rápida (Blanco, Negro, Dorado, etc.).
    - Cajas de fondo para legibilidad sobre fotos (sin fondo, caja negra translúcida 55%, caja negra sólida, caja blanca translúcida 65%, caja blanca sólida).
    - Control de interlineado y margen interior de seguridad.
  - La sección del **CD** aplica recorte circular suave (antialiasing) con diámetro exterior y agujero central configurable.
  - Visualización del tamaño real de impresión, área de seguridad (1.5 mm verde) y sangrado (rojo).
  - **Maqueta de Conjunto:** visualización 2D/3D del estuche mini CD transparente ensamblado junto con el disco.

- **Modo Automático (Generador Rápido):**
  - **Previsualización interactiva simultánea:** al elegir las fotos, muestra en tiempo real cómo se adecuan y cortan tanto la portada rectangular como la etiqueta circular del CD, permitiendo arrastrar el encuadre con el ratón directamente dentro del asistente.
  - Reutilización inteligente de la portada para el CD o selección de imágenes independientes.
  - **Paso Final con Exportación Inmediata a PDF:**
    - Opción para elegir la ruta y carpeta de destino donde se guardará el PDF listo para imprimir.
    - Opción para abrir el archivo PDF inmediatamente al generarse para enviar a imprimir en un solo paso.
    - Botón directo de exportación inmediata o botón para continuar refinando en el Diseñador.

### 2. Sistema de Perfiles de Medidas Persistente
- Las dimensiones exteriores del estuche se almacenan como **referencia física** y no interfieren con las medidas de corte e impresión.
- Permite crear nuevos perfiles, duplicarlos, renombrarlos y editarlos en milímetros con precisión decimal.
- Perfiles de fábrica identificados con medidas provisionales:
  - *Mini CD Estuche Estándar 50x50 mm (Provisional)*
  - *Mini CD Estuche Compacto 45x45 mm (Provisional)*
  - *Mini CD Inlay Continuo Desplegado (Provisional)* (para imprimir portada + lomo + contraportada en una sola tira para plegar).
- Persistencia local en `%APPDATA%/NFCitoStudio/profiles.json`.
- Recuerda automáticamente el último perfil activo al reiniciar la aplicación.
- **Cambiar de perfil actualiza el lienzo y las dimensiones sin borrar las imágenes ni el trabajo del usuario.**

### 3. Organización de la Hoja de Impresión
- Selección de formatos: A4, Carta (Letter), Oficio (Legal), A5, 4x6" foto, etc.
- Orientación vertical u horizontal.
- Algoritmo de empaquetado inteligente que garantiza **cero superposiciones**.
- Repetición y cantidades configurables por pieza (por ejemplo, imprimir 4 etiquetas de CD o 2 álbumes completos).
- Generación automática de múltiples páginas si la cantidad excede una sola hoja.
- Detección de márgenes no imprimibles de impresora doméstica (5 mm) con advertencias visuales si alguna pieza corre riesgo de cortarse.

### 4. Exportación PDF de Alta Precisión
- Conversión exacta de milímetros a puntos PostScript/PDF (`1 mm = 72 / 25.4 pt`).
- Renderizado de imágenes a 300 DPI de resolución de imprenta.
- Marcas de corte esquineras discretas y líneas guía de plegado de lomo.
- **Página de Calibración de Escala Obligatoria:** incluye un recuadro de **50.0 × 50.0 mm** con marcas milimétricas para verificar con una regla física que la impresora está trabajando al 100% de escala real sin distorsión.

### 5. Gestión de Proyectos (.nfcito)
- Guardado y carga de proyectos completos.
- Empaquetado automático de imágenes en una subcarpeta `[proyecto]_assets` para que los archivos no dependan de rutas temporales.
- Detección de imágenes faltantes y comunicación clara al usuario mediante avisos comprensibles.

### 6. Preparación para Etiquetas NFC
- Campos dedicados para Título del Álbum, Artista, Canción, Enlace de destino (Spotify, Apple Music, YouTube) y Tipo de etiqueta NFC (`NTAG213`, `NTAG215`, `NTAG216`).

---

## 🛠️ Requisitos e Instalación en Windows

### Requisitos Previos
- **Windows 10 o Windows 11**.
- **Python 3.10 o superior** (probado y verificado en Python 3.14).

### Instalación de Dependencias
Abra un terminal PowerShell en la carpeta del proyecto y ejecute:
```powershell
pip install -r requirements.txt
```

O instalando individualmente:
```powershell
pip install PySide6 Pillow reportlab pytest
```

---

## 🖥️ Cómo Ejecutar la Aplicación

Desde la terminal en el directorio raíz del proyecto:
```powershell
python run_app.py
```

O ejecutando el módulo:
```powershell
python -m nfcito.app
```

---

## 🧪 Pruebas Automatizadas

El proyecto cuenta con una suite completa de pruebas unitarias y de integración que cubren los requisitos críticos:

```powershell
python -m pytest -v
```

### Resultados de la Suite de Pruebas:
| Módulo de Prueba | Funcionalidad Verificada | Resultado |
|---|---|:---:|
| `test_profiles.py` | Guardado y recuperación persistente en JSON | ✅ PASS |
| `test_profiles.py` | Restauración del último perfil activo al iniciar | ✅ PASS |
| `test_profiles.py` | Conservación de perfiles previos al crear uno nuevo | ✅ PASS |
| `test_profiles.py` | Duplicación y renombrado de perfiles | ✅ PASS |
| `test_project_preservation.py` | Cambiar de perfil conserva imágenes y recortes | ✅ PASS |
| `test_project_preservation.py` | Guardado y carga de proyectos (.nfcito) | ✅ PASS |
| `test_project_preservation.py` | Comunicación clara de imágenes no disponibles | ✅ PASS |
| `test_image_ops.py` | Recorte proporcional sin deformación de aspecto | ✅ PASS |
| `test_image_ops.py` | Máscara circular de CD y agujero central transparente | ✅ PASS |
| `test_image_ops.py` | Renderizado de textos y tracklist de contraportada | ✅ PASS |
| `test_layout_engine.py` | Cero superposiciones entre piezas en la hoja | ✅ PASS |
| `test_layout_engine.py` | Detección de piezas que exceden el papel imprimible | ✅ PASS |
| `test_layout_engine.py` | Distribución multipágina automática | ✅ PASS |
| `test_layout_engine.py` | Diagramación de bandeja continua desplegada (inlay) | ✅ PASS |
| `test_pdf_export.py` | Precisión matemática milímetros a puntos PDF | ✅ PASS |
| `test_pdf_export.py` | Generación de PDF con página de calibración 50x50 mm | ✅ PASS |
| `test_pdf_export.py` | Exportación de piezas rectangulares y circulares | ✅ PASS |

---

## 📐 Guía de Impresión y Calibración Física

1. Abra **Herramientas > Calibración de Escala (50 × 50 mm)...** o active la casilla de calibración en la ventana de impresión.
2. Al abrir el PDF en Adobe Acrobat, Foxit Reader o el navegador:
   - **Desactive:** *"Ajustar a página"* o *"Fit to printable area"*.
   - **Active:** **"Tamaño Real"** o **"Escala 100%"**.
3. Imprima en el papel fotográfico deseado.
4. Con una regla milimétrica o calibre, mida el recuadro de calibración de la primera página:
   - Debe medir exactamente **50.0 mm × 50.0 mm**.
5. Corte las piezas guiándose por las marcas esquineras o contornos circulares.

---

## 📁 Estructura del Proyecto

```
Llaveros/
├── nfcito/
│   ├── __init__.py
│   ├── config.py              # Rutas en APPDATA y configuración global
│   ├── app.py                 # Arranque de la aplicación Qt
│   ├── models/
│   │   ├── __init__.py
│   │   ├── profile.py         # CaseProfile, PieceDimension, CDDimension
│   │   ├── project.py         # Project, PieceDesign, CropConfig, TextConfig, NFCConfig
│   │   └── sheet.py           # PlacedItem, PrintPage, LayoutResult
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── profile_repo.py    # Persistencia JSON y CRUD de perfiles
│   │   └── project_repo.py    # Guardado .nfcito con empaquetado de assets
│   ├── core/
│   │   ├── __init__.py
│   │   ├── units.py           # Conversiones mm <-> pt <-> px @ DPI
│   │   ├── image_ops.py       # Procesamiento Pillow, recortes, máscaras CD, textos
│   │   ├── layout_engine.py   # Algoritmo de empaquetado y prevención de colisiones
│   │   └── pdf_exporter.py    # Motor ReportLab de alta resolución y calibración
│   └── gui/
│       ├── __init__.py
│       ├── styles.py          # Tema visual moderno (QSS)
│       ├── main_window.py     # Ventana principal e integración de componentes
│       ├── canvas_view.py     # Lienzo de edición con arrastre, zoom y guías
│       ├── composite_view.py  # Maqueta del mini estuche y disco ensamblados
│       ├── properties_dock.py # Panel lateral de medidas, recorte, textos y NFC
│       └── dialogs/
│           ├── __init__.py
│           ├── profile_manager.py # Administrador de perfiles de estuches
│           ├── quick_generator.py # Asistente del modo automático
│           ├── print_layout.py    # Organizador de hojas y exportación
│           └── calibration.py     # Hoja de calibración 50x50 mm
├── tests/
│   ├── __init__.py
│   ├── test_profiles.py
│   ├── test_project_preservation.py
│   ├── test_image_ops.py
│   ├── test_layout_engine.py
│   └── test_pdf_export.py
├── run_app.py                 # Script directo de ejecución
├── requirements.txt           # Dependencias de Python
└── README.md                  # Documentación completa en español
```

---

## 💡 Limitaciones Conocidas y Recomendaciones
- **Escritura física NFC:** Esta versión almacena y organiza los metadatos NFC (URL de destino, título, artista y tipo de chip) listos para proyectos y catálogos, pero no realiza la escritura por hardware RFID/NFC en el tag físico (requiere lector ACR122U / smartphone externo).
- **Tipografías:** Los textos de contraportada utilizan fuentes estándar del sistema (`Arial` o tipografía de reserva) para máxima compatibilidad sin depender de licencias externas.
