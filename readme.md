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

# Datos recibidos

Estructura del Frame: Cada respuesta de 64 bytes contiene 4 bloques de 16 bytes cada uno. 

Ubicación de los Datos: El Tag está en los bytes 3 a 9 (6 bytes) y la Fecha en los bytes 10 a 14 (4 bytes). 

Codificación de la Fecha: Es un entero de 32 bits Big Endian con un empaquetado de bits específico (Segundos al inicio, Año al final).

Procesar lecturas

Bloque recibido:
Indice		
00 08 FE 00 | 59 00 67 5F 2B | 00 04 57 10 9A 00 00

Hay 5 tag almacenados
*  Tag1=10006F0C09 2026-02-05 16:25:03
*  Tag2=2300849c30 2026-02-05 16:25:11
*  Tag3=090053f1b0 2026-02-05 16:25:18
*  Tag4=090053e0a4 2026-02-05 16:25:24
*  Tag5=5900675f2b 2026-02-05 16:25:29
Frames enviados por la sonda, contiene cuatro tag con fecha asosida por frame
HID Data: 0009160010006f0c09000d98189a0000000917002300849c30002d98189a000000091800090053f1b0004998189a000000091900090053e0a4006198189a0000
HID Data: 00091a005900675f2b007598189a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

dividimos los frames en cuatro bloques

0009160010006f0c09000d98189a0000
000917002300849c30002d98189a0000
00091800090053f1b0004998189a0000
00091900090053e0a4006198189a0000
00091a005900675f2b007598189a0000
00000000000000000000000000000000 > finaliza al encontrar el vacio

extraemos de cada bloque los datos asociados al tag

[0,5] puntero_indice (3 bytes) = 000916 
[6,17] id_tag (6 bytes) = 0010006f0c09 
[18,20] reservado_1 (3 bits) = 000
[21,27] tiempo_registro ( bits)= d98189a 
[28,31] reservado_2 (2 bytes)= 0000

Extraccion de tiempo_registro
Tag 1 = tiempo_registro = d98189a = 32 bits
Empaquetado ssssss mmmmmm HHHHH DDDDD AAAAAA
6 bits segundos
6 bits minutos
5 bits hora
5 bits dia
4 bits mes
6 bits año (acumulados desde 2000)

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

# Byte Offset, Descripción,         Tamaño,  Ejemplo (Hex)
# 0 - 2,       Índice (Puntero),   3 bytes,  00 09 16
# 3 - 8,       ID TAG,             6 bytes,  00 10 00 6F 0C 09
# 9,           Reservado,          1 byte,   00
# 10 - 13,     FECHA (32 bits),    4 bytes,  0D 98 18 9A
# 14 - 15,     Reservado,          2 bytes,  00 00


## 🚀 Instalación y Uso

1. **Requisitos:**
   - Python 3.x
   - PyUSB: `pip install pyusb`
   - Backend de USB (libusb-1.0 o similar según el SO).

2. **Ejecución:**
   
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

## 🚀 Instalación rápida git

1. Clona el repositorio:
   
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


## 🚀 MantenimientoIstalacion de la aplicacion (git)

1. Clona el repositorio:
   
   git clone [https://github.com/Flav10R/PatrolApp.git]
   (https://github.com/Flav10R/PatrolApp.git)
   
   cd PatrolApp



2. **Entorno Virtual (venv)**

   Crear
   python -m venv .venv
   Activar
   .venv\Scripts\activate 

3. Instalar las dependencias:
   bash
   pip install -r requirements.txt   

# *** Mantenimineto ***
1. Subir los cambios a GitHub

   git add .
   git commit -m "Añadido archivo de requerimientos y guía de instalación"
   git push origin main
   Utiles:
   git rm -r --cached ~~build/ dist/~~ ~~*.spec~~ Borra los archivos agregados con add . que no deben subirse  

# Compilar codigo
1. intalar pyinstaller
    pip install pyinstaller
2. Ejecutar
    pyinstaller --onefile --console --name PatrolApp_1.1  main.py
    Usar --console ya que no tiene interfaz grafica