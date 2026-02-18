import usb.core
import usb.util
import datetime
import time
import os

class SondaGS6200:
    # Comandos de la sonda
    CMD_GET_ID     = 0x0F
    CMD_DOWNLOAD   = 0x31
    CMD_GET_RTC    = 0x20
    CMD_SET_RTC    = 0x21
    CMD_REREAD     = 0x34  # Comando vital para volver atrás si sale todo 00

    def __init__(self, vid=0x0483, pid=0x5750, log_callback=None):
        self.vid = vid
        self.pid = pid
        self.device = None
        self.ep_in = None
        self.ep_out = None
        self.log_callback = log_callback

    def log(self, mensaje):
        if self.log_callback:
            self.log_callback(f"[Sonda] {mensaje}")

    def _gestionar_archivos_log(self):
        """Maneja la rotación de logs: log.txt -> log.bak"""
        archivo_log = "log.txt"
        archivo_bak = "log.bak"
        try:
            if os.path.exists(archivo_bak):
                os.remove(archivo_bak)
            if os.path.exists(archivo_log):
                os.rename(archivo_log, archivo_bak)
        except Exception as e:
            print(f"[Aviso] No se pudo rotar logs: {e}")

    def conectar(self):
        try:
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            if self.device is None: return False

            self.device.set_configuration()
            cfg = self.device.get_active_configuration()
            intf = cfg[(0,0)]

            self.ep_in = usb.util.find_descriptor(
                intf, 
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            self.ep_out = usb.util.find_descriptor(
                intf, 
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            return True if self.ep_in and self.ep_out else False
        except Exception as e:
            print(f"DEBUG: Error en conexión: {e}")
            return False

    def _enviar_comando(self, cmd, datos_extra=None):
        if not self.device: return None
        # Estructura estándar: [02 0F 0F 0F 10 CMD ...]
        buffer = [0x02, 0x0F, 0x0F, 0x0F, 0x10, cmd]
        if datos_extra:
            buffer.extend(datos_extra)
        
        # Rellenar hasta 64 bytes
        buffer += [0x00] * (64 - len(buffer))
        
        try:
            self.ep_out.write(buffer)
            res = self.ep_in.read(64, timeout=2000)
            time.sleep(0.1) # Pequeña pausa para estabilidad
            return list(res)
        except Exception as e:
            self.log(f"Error IO: {e}")
            return None

    def re_leer_registros(self, cantidad):
        """ Mueve el puntero de lectura atrás N registros """
        # Convertimos el entero a 4 bytes Little Endian
        datos = list(cantidad.to_bytes(4, byteorder='little'))
        res = self._enviar_comando(self.CMD_REREAD, datos)
        # Verificamos si la sonda respondió con el mismo comando (éxito)
        if res and len(res) > 5 and res[5] == self.CMD_REREAD:
            return True
        return False

    def obtener_id(self):
        res = self._enviar_comando(self.CMD_GET_ID)
        return int.from_bytes(res[10:14], byteorder='big') if res else None

    def obtener_rtc(self):
        res = self._enviar_comando(self.CMD_GET_RTC)
        if not res: return None
        bcd = lambda b: (b >> 4) * 10 + (b & 0x0F)
        try:
            return datetime.datetime(2000+bcd(res[12]), bcd(res[10]), bcd(res[9]), 
                                     bcd(res[8]), bcd(res[7]), bcd(res[6]))
        except: return None

    def descargar_datos(self):
        # 1. Preparar sistema de archivos
        self._gestionar_archivos_log()
        ahora = datetime.datetime.now()
        nombre_ronda = ahora.strftime("ronda_%d%m%y%H%M.txt")
        registros = []
        
        print(f"Guardando datos en: {nombre_ronda}")

        try:
            with open("log.txt", "w") as f_log, open(nombre_ronda, "w") as f_ronda:
                f_log.write(f"Inicio descarga: {ahora}\n")
                
                while True:
                    # Solicitamos bloque de datos (Comando 0x31)
                    res = self._enviar_comando(self.CMD_DOWNLOAD)
                    
                    if not res: break
                    
                    # Logueamos lo crudo para debug
                    raw_hex = bytes(res).hex().upper()
                    f_log.write(f"RAW: {raw_hex}\n")

                    # Si recibimos todo ceros, es probable que no haya más datos
                    if not any(res):
                        break

                    encontrado_en_este_frame = False
                    
                    # Procesamos los 4 sub-bloques de 16 bytes
                    for i in range(0, 64, 16):
                        bloque = res[i:i+16]
                        
                        # Si el bloque comienza vacío (índice 00 00 00), saltamos
                        if not any(bloque[0:3]):
                            continue

                        # --- EXTRACCIÓN SEGÚN TU DOCUMENTACIÓN ---
                        # Indice: bloque[0:3]
                        # Tag:    bloque[3:9]  (6 bytes)
                        # Fecha:  bloque[10:14] (4 bytes)
                        
                        tag_raw = bytes(bloque[3:9])
                        tag = tag_raw.hex().upper()
                        
                        # Validamos que sea un Tag real y no basura
                        if any(tag_raw) and tag != "000000000000":
                            fecha_raw = bloque[10:14]
                            
                            # Decodificación BIG ENDIAN (Confirmada por doc)
                            d = int.from_bytes(fecha_raw, byteorder='big')
                            
                            # Mapeo de bits: ssssss mmmmmm HHHHH DDDDD MMMM AAAAAA
                            seg = (d >> 26) & 0x3F
                            mi  = (d >> 20) & 0x3F
                            ho  = (d >> 15) & 0x1F
                            di  = (d >> 10) & 0x1F
                            me  = (d >> 6)  & 0x0F
                            an  = 2000 + (d & 0x3F)
                            
                            try:
                                fecha_dt = datetime.datetime(an, me, di, ho, mi, min(seg, 59))
                                
                                # Formateamos la salida
                                linea = f"{tag} {fecha_dt.strftime('%d/%m/%Y %H:%M:%S')}"
                                
                                registros.append({"tag": tag, "fecha": fecha_dt})
                                f_ronda.write(linea + "\n")
                                f_log.write(f"  [OK] {linea}\n")
                                encontrado_en_este_frame = True
                                
                            except Exception as e:
                                f_log.write(f"  [ERROR FECHA] {tag} -> {an}-{me}-{di} ({e})\n")
                                continue

                    if not encontrado_en_este_frame:
                        # Si el frame tiene datos pero no pudimos sacar tags, 
                        # puede ser fin de memoria o basura.
                        # Verificamos si todo el buffer es 00 o FF
                        if not any(res): break

        except Exception as e:
            print(f"Error escribiendo archivos: {e}")

        return registros