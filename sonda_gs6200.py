import usb.core
import usb.util
import datetime
import time
import os

class SondaGS6200:
    # Diccionario de comandos confirmados
    CMD_GET_ID    = 0x0F  # Obtener Serial
    CMD_DOWNLOAD  = 0x31  # Descargar registros (de a 2 por bloque)
    CMD_GET_RTC   = 0x20  # Leer hora actual
    CMD_SET_RTC   = 0x21  # Sincronizar hora
    CMD_REREAD    = 0x34  # Volver a leer N registros (usa 4 bytes datos)
    CMD_INITIALIZE = 0x52  # Inicializar/Borrar memoria

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

    def conectar(self):
        try:
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            if self.device is None: return False
            
            self.device.set_configuration()
            cfg = self.device.get_active_configuration()
            intf = cfg[(0,0)]
            
            self.ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
            self.ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
            
            return True if self.ep_in and self.ep_out else False
        except Exception as e:
            self.log(f"Error de conexión: {e}")
            return False

    def _enviar_comando(self, cmd, datos_extra=None):
        """ Gestiona el empaquetado de 64 bytes para el USB HID """
        if not self.device: return None
        
        # Trama estándar: [02 0F 0F 0F 10 CMD ...]
        buffer = [0x02, 0x0F, 0x0F, 0x0F, 0x10, cmd]
        if datos_extra:
            buffer.extend(datos_extra)
        
        # Rellenar hasta 64 bytes
        buffer += [0x00] * (64 - len(buffer))
        
        try:
            self.ep_out.write(buffer)
            res = self.ep_in.read(64, timeout=2000)
            time.sleep(0.1) # Estabilidad del bus
            return list(res)
        except Exception as e:
            self.log(f"Error en comando {hex(cmd)}: {e}")
            return None

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

    def enviar_hora(self, dt):
        to_bcd = lambda v: ((v // 10) << 4) | (v % 10)
        # Seg, Min, Hor, Dia, Mes, Siglo(20), Año(YY)
        datos = [to_bcd(dt.second), to_bcd(dt.minute), to_bcd(dt.hour), 
                 to_bcd(dt.day), to_bcd(dt.month), 0x20, to_bcd(dt.year % 100)]
        res = self._enviar_comando(self.CMD_SET_RTC, datos)
        return True if res and res[5] == self.CMD_SET_RTC else False

    def re_leer_registros(self, cantidad):
        """ Mueve el puntero de lectura atrás N registros """
        datos = list(cantidad.to_bytes(4, byteorder='little'))
        res = self._enviar_comando(self.CMD_REREAD, datos)
        return True if res and res[5] == self.CMD_REREAD else False

    def inicializar_memoria(self):
        """ Borra o resetea la memoria de la sonda """
        res = self._enviar_comando(self.CMD_INITIALIZE)
        return True if res and res[5] == self.CMD_INITIALIZE else False

    def _gestionar_archivos_log(self):
        """Maneja la rotación de logs: log.txt -> log.bak"""
        archivo_log = "log.txt"
        archivo_bak = "log.bak"

        try:
            # 1. Si existe un backup anterior, lo borramos
            if os.path.exists(archivo_bak):
                os.remove(archivo_bak)
            
            # 2. Si existe un log actual, lo renombramos a backup
            if os.path.exists(archivo_log):
                os.rename(archivo_log, archivo_bak)
                
        except Exception as e:
            print(f"[Aviso] No se pudo rotar logs: {e}")

    def descargar_datos(self):
        # 1. Gestionar rotación de logs crudos
        self._gestionar_archivos_log()
        
        # 2. Generar nombre del archivo de la ronda: ronda_ddMMAAHHMM.txt
        ahora = datetime.datetime.now()
        nombre_ronda = ahora.strftime("ronda_%d%m%y%H%M.txt")
        
        registros = []
        
        # Abrimos ambos archivos: el log crudo y el archivo de la ronda
        try:
            with open("log.txt", "w") as f_log, open(nombre_ronda, "w") as f_ronda:
                f_log.write(f"Inicio descarga: {ahora}\n")
                
                while True:
                    res = self._enviar_comando(self.CMD_DOWNLOAD)
                    if not res: break
                    
                    # Log crudo (hexadecimal)
                    f_log.write(f"RAW: {bytes(res).hex().upper()}\n")

                    encontrado_en_este_frame = False
                    
                    # Procesar los 4 sub-bloques de 16 bytes
                    for i in range(0, 64, 16):
                        bloque = res[i:i+16]
                        
                        # Si el índice (primeros 3 bytes) es cero, saltar
                        if not any(bloque[0:3]):
                            continue

                        # Extracción según documentación
                        tag_raw = bytes(bloque[3:9])
                        tag = tag_raw.hex().upper()
                        
                        fecha_raw = bloque[10:14]
                        d = int.from_bytes(fecha_raw, byteorder='big')
                        
                        # Decodificación de bits
                        seg = (d >> 26) & 0x3F
                        mi  = (d >> 20) & 0x3F
                        ho  = (d >> 15) & 0x1F
                        di  = (d >> 10) & 0x1F
                        me  = (d >> 6)  & 0x0F
                        an  = 2000 + (d & 0x3F)
                        
                        try:
                            fecha_dt = datetime.datetime(an, me, di, ho, mi, min(seg, 59))
                            
                            # Formato solicitado: 0010006F0C09 16/02/2026 14:31:22
                            linea_formateada = f"{tag} {fecha_dt.strftime('%d/%m/%Y %H:%M:%S')}"
                            
                            # Guardar en lista para retorno
                            registros.append({"tag": tag, "fecha": fecha_dt})
                            
                            # Guardar en archivo de la ronda
                            f_ronda.write(linea_formateada + "\n")
                            
                            # Loguear éxito
                            f_log.write(f"  [OK] {linea_formateada}\n")
                            encontrado_en_este_frame = True
                            
                        except Exception as e:
                            f_log.write(f"  [ERROR FECHA] {an}-{me}-{di}\n")
                            continue

                    if not encontrado_en_este_frame:
                        break
                        
            print(f"[EXITO] Datos guardados en {nombre_ronda}")
            
        except Exception as e:
            self.log(f"Error al escribir archivos: {e}")
            
        return registros
    
    # def descargar_datos(self):
    #     registros = []
    #     while True:
    #         # Leemos 64 bytes de la sonda
    #         res = self._enviar_comando(self.CMD_DOWNLOAD)
            
    #         # Verificamos si la respuesta es válida
    #         if not res or (len(res) > 5 and res[5] != self.CMD_DOWNLOAD): 
    #             # Nota: A veces la primera respuesta puede variar, 
    #             # si falla mucho, quita la condición "res[5] !="
    #             break
            
    #         encontrado_en_este_frame = False
            
    #         # PROCESAMIENTO EFICAZ: Dividimos en 4 bloques de 16 bytes
    #         # Bloque 1: 0-16, Bloque 2: 16-32, Bloque 3: 32-48, Bloque 4: 48-64
    #         for i in range(0, 64, 16):
    #             bloque = res[i:i+16]
                
    #             # Verificamos si el bloque está vacío (puros ceros)
    #             # Si los primeros bytes son 00, asumimos fin de datos
    #             if not any(bloque[0:10]):
    #                 continue

    #             # --- 1. EXTRACCIÓN DEL TAG (Bytes 3 al 9) ---
    #             tag_raw = bytes(bloque[3:9])
    #             tag = tag_raw.hex().upper()
                
    #             # --- 2. EXTRACCIÓN DE LA FECHA (Bytes 10 al 14) ---
    #             fecha_raw = bloque[10:14]
                
    #             # CRÍTICO: Tu documentación muestra que los bits se leen en orden 
    #             # (Seg, Min, Hora...), esto corresponde a BIG ENDIAN.
    #             d = int.from_bytes(fecha_raw, byteorder='big')
                
    #             # --- 3. DECODIFICACIÓN DE BITS ---
    #             # Estructura según tu archivo:
    #             # 6b Seg | 6b Min | 5b Hora | 5b Dia | 4b Mes | 6b Año
    #             # Total 32 bits. Usamos desplazamiento (>>) y máscaras (&)
                
    #             seg = (d >> 26) & 0x3F  # Primeros 6 bits (MSB)
    #             mi  = (d >> 20) & 0x3F  # Siguientes 6 bits
    #             ho  = (d >> 15) & 0x1F  # Siguientes 5 bits
    #             di  = (d >> 10) & 0x1F  # Siguientes 5 bits
    #             me  = (d >> 6)  & 0x0F  # Siguientes 4 bits
    #             an  = 2000 + (d & 0x3F) # Últimos 6 bits (LSB)
                
    #             try:
    #                 fecha = datetime.datetime(an, me, di, ho, mi, min(seg, 59))
    #                 registros.append({"tag": tag, "fecha": fecha})
    #                 encontrado_en_este_frame = True
    #                 print(f"DEBUG: Tag {tag} | Fecha {fecha}") # Para verificar en consola
    #             except Exception as e:
    #                 # Si la fecha es inválida (ej: ceros), ignoramos el registro
    #                 continue

    #         # Si en todo el frame de 64 bytes no encontramos nada válido, terminamos
    #         if not encontrado_en_este_frame:
    #             break
                
    #     return registros