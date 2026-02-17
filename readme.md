# PatrolApp - Gestor de Sonda GS-6200

Software de comunicación y gestión para la sonda de control de rondas **GS-6200**. Este proyecto permite la extracción de registros, sincronización de reloj y mantenimiento de memoria a través de una conexión USB HID.

## 📋 Características

- **Sincronización RTC:** Ajuste del reloj interno de la sonda (PC -> Sonda) mediante formato BCD.
- **Descarga de Datos:** Extracción de registros almacenados con decodificación de estampa de tiempo (Bit-Packing).
- **Control de Punteros:** Capacidad de re-leer registros específicos mediante el comando `0x34`.
- **Mantenimiento:** Inicialización y borrado de memoria flash mediante el comando `0x52`.

## 🛠 Estructura del Proyecto

- `main.py`: Interfaz de usuario por consola y flujo de la aplicación.
- `sonda_gs6200.py`: Driver de bajo nivel que gestiona el protocolo USB y la lógica de bits.
- `descargas/`: (Carpeta sugerida) Almacenamiento de archivos `.txt` con los registros extraídos.

## 📡 Protocolo de Comunicación

La comunicación se realiza mediante tramas de **64 bytes**.

### Comandos Implementados
| HEX | Descripción | Función |
| :--- | :--- | :--- |
| `0x0F` | Get Serial | Obtiene el ID único del dispositivo. |
| `0x20` | Get RTC | Lee la fecha y hora actual del reloj interno. |
| `0x21` | Set RTC | Sincroniza la hora enviando datos en BCD. |
| `0x31` | Download | Descarga registros de a 2 por bloque (32 bytes c/u). |
| `0x34` | Re-read | Retrocede el puntero de lectura N registros. |
| `0x52` | Initialize | Formatea o resetea la memoria de registros. |

## 🧩 Decodificación de Fecha (Bit-Packing)

La sonda optimiza el espacio de memoria empaquetando la fecha y hora en un bloque de 32 bits (4 bytes) dentro del campo `date` de cada registro:

**Formato:** `ssssss mmmmmm HHHHH DDDDD MMMM AAAAAA` (de LSB a MSB)

| Campo | Bits | Rango |
| :--- | :--- | :--- |
| **Segundos** | 6 (0-5) | 0-59 |
| **Minutos** | 6 (6-11) | 0-59 |
| **Horas** | 5 (12-16) | 0-23 |
| **Día** | 5 (17-21) | 1-31 |
| **Mes** | 4 (22-25) | 1-12 |
| **Año** | 6 (26-31) | 2000-2063 |



## 🚀 Instalación y Uso

1. **Requisitos:**
   - Python 3.x
   - PyUSB: `pip install pyusb`
   - Backend de USB (libusb-1.0 o similar según el SO).

2. **Ejecución:**
   ```bash
   python main.py

IMPORTANTE

**WinUSB** es un driver genérico que ya viene incluido dentro de Windows, pero el sistema no lo asigna automáticamente a dispositivos como tu sonda (que normalmente se identifican como "HID"). La herramienta **Zadig** es la que se encarga de hacer el "puente".

Pasos exactos para hacerlo correctamente:

### Pasos con Zadig:

1. **Descarga Zadig:** Ve a [zadig.akeo.ie](https://zadig.akeo.ie/) y descarga el ejecutable (no requiere instalación).
2. **Conecta la Sonda:** Asegúrate de que la sonda esté conectada al puerto USB.
3. **Ejecuta Zadig:**
* Ve al menú **Options** y marca **List All Devices**.
* En el desplegable principal, busca tu sonda (debería aparecer algo como "STM32..." o "USB HID Device" con el ID `0483 5750`).


4. **Selecciona el Driver:**
* A la derecha de la flecha verde, asegúrate de que esté seleccionado **WinUSB (v6.x.x.x)**.


5. **Reemplaza el Driver:** Haz clic en el botón grande que dice **Replace Driver** (o *Reinstall Driver*).



### ¿Por qué hacemos esto?

Por defecto, Windows usa un driver "HID" para la sonda. Ese driver es muy celoso y no deja que librerías externas como `pyusb` (que usa tu script) le den órdenes directas. Al cambiarlo a **WinUSB**, le quitas el control a Windows y se lo das a tu aplicación de Python.

### Una vez terminado el proceso:

1. Vuelve a tu terminal en VS Code (con el `.venv` activo).
2. Corre tu aplicación: `python main.py`.
3. Prueba la **Opción 1** (Conectar).

Si todo sale bien, la sonda debería responder "Sonda conectada correctamente" 

📝 Notas de Versión
v1.0.0: Implementación de driver USB, decodificación de bits y menú de gestión básica.

## 🚀 Instalación rápida

1. Clona el repositorio:
   ```bash
   git clone [https://github.com/Flav10R/PatrolApp.git](https://github.com/Flav10R/PatrolApp.git)
   cd PatrolApp

2. Instala las dependencias:
   pip install -r requirements.txt

3. Para ejecutar la **PatrolApp**, necesita instalar las "dependencias".

   Crear el archivo `requirements.txt`

   En la terminal, dentro de tu carpeta `PatrolApp`, crearlo automáticamente ejecutando:

   pip freeze > requirements.txt
   
   **O mejor aún**, créalo manualmente para que sea más limpio y solo contenga lo estrictamente necesario.


   pyusb==1.2.1
   libusb-package==1.0.26.2



   **Nota:**
   Se ha incluido `libusb-package` porque en Windows ayuda muchísimo a que Python encuentre los drivers USB  sin complicaciones extras.


### Cómo se instalan las librerías

Ahora, cuando alguien descargue tu proyecto de GitHub, solo tendrá que abrir una terminal y escribir:


   pip install -r requirements.txt


Esto instalará todo de una sola vez.


## 🚀 Instalación rápida de la aplicacion (git)

1. Clona el repositorio:
   
   git clone [https://github.com/Flav10R/PatrolApp.git]
   (https://github.com/Flav10R/PatrolApp.git)
   
   cd PatrolApp

2. Subir los cambios a GitHub

   git add .
   git commit -m "Añadido archivo de requerimientos y guía de instalación"
   git push origin main


3. **Entorno Virtual (venv)**
   Crear
   python -m venv .venv
   Activar
   .venv\Scripts\activate 

4. Instala las dependencias:
   bash
   pip install -r requirements.txt   