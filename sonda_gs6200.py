import usb.core
import usb.util
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
        self.ep_in = None
        self.ep_out = None
        self.log_callback = log_callback

    def _gestionar_archivos_log(self):
        """ Limpieza de archivos temporales """
        if os.path.exists("log.bak"): os.remove("log.bak")
        if os.path.exists("log.txt"): os.rename("log.txt", "log.bak")

    def conectar(self):
        """ Intento de conexión robusto con reintentos y reset """
        intentos = 3
        for i in range(intentos):
            try:
                self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
                if self.device:
                    time.sleep(0.2)
                    try:
                        self.device.reset()
                        time.sleep(0.3)
                    except: pass
                    
                    self.device.set_configuration()
                    cfg = self.device.get_active_configuration()
                    intf = cfg[(0,0)]
                    self.ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
                    self.ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
                    
                    if self.ep_in and self.ep_out:
                        return True
                time.sleep(0.5)
            except Exception as e:
                if i == intentos - 1: print(f"DEBUG Error USB: {e}")
                time.sleep(0.5)
        return False

    def _enviar_comando(self, cmd, datos_extra=None):
        if not self.device: return None
        buffer = [0x02, 0x0F, 0x0F, 0x0F, 0x10, cmd]
        if datos_extra: buffer.extend(datos_extra)
        buffer += [0x00] * (64 - len(buffer))
        try:
            self.ep_out.write(buffer)
            res = self.ep_in.read(64, timeout=2000)
            return list(res)
        except: return None

    def obtener_id(self):
        res = self._enviar_comando(self.CMD_GET_ID)
        return int.from_bytes(res[10:14], byteorder='big') if res else None

    def obtener_rtc(self):
        res = self._enviar_comando(self.CMD_GET_RTC)
        if res:
            def bcd(b): return (b >> 4) * 10 + (b & 0x0F)
            try:
                # Mapeo: 7:seg, 8:min, 9:hora, 10:día, 11:mes, 12:año
                return datetime.datetime(2000 + bcd(res[12]), bcd(res[11]), bcd(res[10]), 
                                       bcd(res[9]), bcd(res[8]), bcd(res[7]))
            except: return None
        return None

    def enviar_hora(self, dt):
        """ Sincroniza la hora de la PC a la sonda (Opción 3) """
        def to_bcd(v): return ((v // 10) << 4) | (v % 10)
        # s, m, h, d, mes, ?, año
        datos = [to_bcd(dt.second), to_bcd(dt.minute), to_bcd(dt.hour), 
                 to_bcd(dt.day), to_bcd(dt.month), 0x00, to_bcd(dt.year % 100)]
        res = self._enviar_comando(self.CMD_SET_RTC, datos)
        return True if res and res[5] == self.CMD_SET_RTC else False

    def re_leer_registros(self, n):
        datos = list(n.to_bytes(4, byteorder='little'))
        res = self._enviar_comando(self.CMD_REREAD, datos)
        return True if res and res[5] == self.CMD_REREAD else False

    def inicializar_memoria(self):
        res = self._enviar_comando(self.CMD_CLEAR)
        return True if res and res[5] == self.CMD_CLEAR else False

    def descargar_datos(self):
        self._gestionar_archivos_log()
        nombre_ronda = datetime.datetime.now().strftime("ronda_%d%m%y%H%M.txt")
        registros = []
        
        with open("log.txt", "w") as f_log, open(nombre_ronda, "w") as f_ronda:
            while True:
                res = self._enviar_comando(self.CMD_DOWNLOAD)
                # Si el frame es todo ceros o no hay respuesta, terminar
                if not res or not any(res[0:10]): break
                
                f_log.write(f"RAW: {bytes(res).hex().upper()}\n")
                encontrado = False
                for i in range(0, 64, 16):
                    bloque = res[i:i+16]
                    if any(bloque[3:9]): # Validar si hay un Tag
                        tag = bytes(bloque[3:9]).hex().upper()
                        # Decodificación de la fecha GS-6200 (Big Endian bits)
                        d = int.from_bytes(bloque[10:14], byteorder='big')
                        # Mapeo: s(6), m(6), h(5), d(5), mes(4), año(6)
                        fecha = datetime.datetime(2000+(d&0x3F), (d>>6)&0x0F, (d>>10)&0x1F, 
                                               (d>>15)&0x1F, (d>>20)&0x3F, (d>>26)&0x3F)
                        
                        linea = f"{tag} {fecha.strftime('%d/%m/%Y %H:%M:%S')}"
                        registros.append({"tag": tag, "fecha": fecha})
                        f_ronda.write(linea + "\n")
                        encontrado = True
                if not encontrado: break
        return registros