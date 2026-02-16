import usb.core
import usb.util
import datetime
import time

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

    def descargar_datos(self):
        """ Lee todos los registros disponibles usando el bit-packing decodificado """
        registros = []
        while True:
            res = self._enviar_comando(self.CMD_DOWNLOAD)
            if not res or not any(res[0:16]): break
            
            for i in range(0, 64, 32):
                bloque = res[i:i+32]
                if not any(bloque[0:3]): continue # Índice vacío
                
                tag = bloque[9:21].hex().upper()
                d = int.from_bytes(bloque[23:27], byteorder='little')
                
                # Mapa: ssssss(6) mmmmmm(6) HHHHH(5) DDDDD(5) MMMM(4) AAAAAA(6)
                seg = (d & 0x3F)
                mi  = (d >> 6) & 0x3F
                ho  = (d >> 12) & 0x1F
                di  = (d >> 17) & 0x1F
                me  = (d >> 22) & 0x0F
                an  = 2000 + ((d >> 26) & 0x3F)
                
                try:
                    fecha = datetime.datetime(an, me, di, ho, mi, min(seg, 59))
                    registros.append({"tag": tag, "fecha": fecha})
                except: continue
        return registros