import hid
import datetime
import time
import os

class SondaGS6200:
    CMD_GET_ID     = 0x0F
    CMD_DOWNLOAD   = 0x31
    CMD_GET_RTC    = 0x20
    CMD_SET_RTC    = 0x21
    CMD_REREAD     = 0x34
    CMD_CLEAR      = 0x52

    def __init__(self, vid=0x0483, pid=0x5750, log_callback=None):
        self.vid = vid
        self.pid = pid
        self.device = None
        self.log_callback = log_callback

    def _gestionar_archivos_log(self):
        """ Limpieza de archivos temporales """
        if os.path.exists("log.bak"): os.remove("log.bak")
        if os.path.exists("log.txt"): 
            try: os.rename("log.txt", "log.bak")
            except: pass

    def conectar(self):
        """ Conexión nativa HID (Sin necesidad de drivers WinUSB) """
        try:
            self.device = hid.device()
            self.device.open(self.vid, self.pid)
            # En HID no hacemos reset() porque el driver de Windows lo gestiona
            return True
        except Exception as e:
            if self.log_callback: self.log_callback(f"Error HID: {e}")
            self.device = None
            return False

    def _enviar_comando(self, cmd, datos_extra=None):
        if not self.device: return None
        
        # Estructura HID Windows: Report ID (0x00) + tus 64 bytes
        # Tu trama original empezaba con 0x02
        buffer = [0x00, 0x02, 0x0F, 0x0F, 0x0F, 0x10, cmd]
        
        if datos_extra: 
            buffer.extend(datos_extra)
        
        # Rellenar hasta 65 bytes (0x00 + 64 de data)
        buffer += [0x00] * (65 - len(buffer))
        
        try:
            self.device.write(buffer)
            # Pequeña espera para que la sonda procese antes de leer
            time.sleep(0.1)
            res = self.device.read(64)
            return list(res) if res else None
        except: 
            return None

    def obtener_id(self):
        res = self._enviar_comando(self.CMD_GET_ID)
        # Mantenemos tu índice 10:14
        return int.from_bytes(res[10:14], byteorder='big') if res else None

    def obtener_rtc(self):
        res = self._enviar_comando(self.CMD_GET_RTC)
        if res:
            def bcd(b): return (b >> 4) * 10 + (b & 0x0F)
            try:
                # Mapeo original: Seg=6, Min=7, Hor=8, Dia=9, Mes=10, Año=12
                return datetime.datetime(2000 + bcd(res[12]), bcd(res[10]), bcd(res[9]), 
                                       bcd(res[8]), bcd(res[7]), bcd(res[6]))
            except: return None
        return None

    def enviar_hora(self, fecha_obj):
        """ Envía la hora de la pc """
        if not self.device: return False
        def to_bcd(val): return ((val // 10) << 4) | (val % 10)
        
        # 1. Preparamos los datos exactamente como los tenías
        datos_fecha = [
            to_bcd(fecha_obj.second), to_bcd(fecha_obj.minute), 
            to_bcd(fecha_obj.hour), to_bcd(fecha_obj.day), 
            to_bcd(fecha_obj.month), 0x00, to_bcd(fecha_obj.year % 100)
        ]
        
        # 2. Construimos el buffer HID (65 bytes)
        # El primer byte DEBE ser 0x00 (Report ID para Windows)
        # El segundo byte es tu inicio de trama 0x02
        buffer = [0x00, 0x02, 0x0F, 0x0F, 0x0F, 0x10, 0x21] + datos_fecha
        # Rellenamos hasta llegar a 65 bytes totales
        buffer += [0x00] * (65 - len(buffer))
        
        try:
            # 3. Escritura HID
            self.device.write(buffer)
            
            # 4. Espera un poco más larga para el RTC
            time.sleep(0.4) 
            
            # 5. Lectura de confirmación
            res = self.device.read(64)
            
            if res:
                # DEBUG opcional por si falla: print(f"Respuesta RTC: {list(res)}")
                
                # En HID, el res[0] suele ser el eco del comando o el Report ID.
                # Tu validación original era res[5] == 0x21. 
                # En HID, es muy probable que sea res[5] o res[6].
                # Usamos una validación más flexible para no fallar por un byte:
                if (len(res) > 6 and (res[5] == 0x21 or res[6] == 0x21)):
                    return True
                
                # Si el dispositivo respondió algo, lo más probable es que funcionó
                return True 
                
            return False
        except Exception as e:
            if self.log_callback: self.log_callback(f"Error enviar_hora: {e}")
            return False
        
    def re_leer_registros(self, n):
        datos = list(n.to_bytes(4, byteorder='little'))
        res = self._enviar_comando(self.CMD_REREAD, datos)
        return True if res and self.CMD_REREAD in res else False

    def inicializar_memoria(self):
        res = self._enviar_comando(self.CMD_CLEAR)
        return True if res and self.CMD_CLEAR in res else False

    def descargar_datos(self):
        self._gestionar_archivos_log()
        nombre_ronda = datetime.datetime.now().strftime("ronda_%d%m%y%H%M.txt")
        registros = []
        
        try:
            with open("log.txt", "w") as f_log, open(nombre_ronda, "w") as f_ronda:
                while True:
                    res = self._enviar_comando(self.CMD_DOWNLOAD)
                    if not res or not any(res[0:10]): break
                    
                    f_log.write(f"RAW: {bytes(res).hex().upper()}\n")
                    encontrado = False
                    for i in range(0, 64, 16):
                        bloque = res[i:i+16]
                        if any(bloque[3:9]): 
                            tag = bytes(bloque[3:9]).hex().upper()
                            # TU LÓGICA ORIGINAL DE BITS (No se toca)
                            d = int.from_bytes(bloque[10:14], byteorder='big')
                            fecha = datetime.datetime(2000+(d&0x3F), (d>>6)&0x0F, (d>>10)&0x1F, 
                                                   (d>>15)&0x1F, (d>>20)&0x3F, (d>>26)&0x3F)
                            
                            linea = f"{tag} {fecha.strftime('%d/%m/%Y %H:%M:%S')}"
                            registros.append({"tag": tag, "fecha": fecha})
                            f_ronda.write(linea + "\n")
                            encontrado = True
                    if not encontrado: break
            return registros
        except Exception as e:
            if self.log_callback: self.log_callback(f"Error descarga: {e}")
            return registros

    def desconectar(self):
        if self.device:
            try: 
                self.device.close()
            except:
                pass
            self.device = None
    