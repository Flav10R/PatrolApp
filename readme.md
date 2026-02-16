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

Configuración de Driver (Windows):
Es posible que se necesite reemplazar el driver original de la sonda por WinUSB utilizando la herramienta Zadig https://zadig.akeo.ie/ para que PyUSB tenga acceso al dispositivo.

📝 Notas de Versión
v1.0.0: Implementación de driver USB, decodificación de bits y menú de gestión básica.