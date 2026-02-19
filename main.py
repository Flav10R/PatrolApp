import os
import datetime
from sonda_gs6200 import SondaGS6200

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def ejecutar_app():
    sonda = SondaGS6200()
    
    while True:
        limpiar_pantalla()
        # Verificamos si el objeto existe y si el puerto sigue respondiendo
        estado = "CONECTADA" if sonda.device else "DESCONECTADA"
        
        print(f"========================================")
        print(f"   PatrolApp - GESTIÓN GS-6200 [{estado}]")
        print(f"========================================")
        print("1. Conectar Sonda")
        print("2. Ver Info (ID y Hora actual)")
        print("3. Sincronizar reloj c/ hora de PC")
        print("4. DESCARGAR REGISTROS")
        print("5. Re-descargar registros")
        print("6. Borrar Memoria Sonda <irreversible!>")
        print("0. Salir")
        print("----------------------------------------")
        
        op = input("Seleccione una opción: ")

        if op == "1":
            if sonda.conectar(): 
                print("\n[OK] Sonda conectada correctamente vía HID.")
            else: 
                print("\n[!] No se detectó la sonda. Verifique conexión.")

        elif op in ["2", "3", "4", "5", "6"] and not sonda.device:
            print("\n[!] Primero debe conectar la sonda (Opción 1).")

        elif op == "2":
            sid = sonda.obtener_id()
            rtc_str = sonda.obtener_rtc() # Ahora devuelve String formateado
            print(f"\nID Dispositivo: {sid if sid else 'Error de lectura'}")
            print(f"Hora en Sonda: {rtc_str}")

        elif op == "3":
            ahora = datetime.datetime.now()
            # Asegúrate de que enviar_hora esté adaptado a HID en sonda_gs6200.py
            if sonda.enviar_hora(ahora):
                print(f"\n[OK] Hora sincronizada: {ahora.strftime('%d/%m/%Y %H:%M:%S')}")
            else:
                print("\n[!] Error al sincronizar hora.")

        elif op == "4":
            print("\nIniciando descarga...")
            datos = sonda.descargar_datos()
            if datos:
                print(f"\n[EXITO] Se procesaron {len(datos)} registros.")
                for reg in datos:
                    # Asumimos que el retorno de descargar_datos es una lista de dicts
                    print(f"TAG: {reg['tag']} | Fecha: {reg['fecha']}")
            else:
                print("\n[?] No se encontraron registros o error de comunicación.")

        elif op == "5":
            try:
                n = int(input("\n¿Cuántos registros hacia atrás desea re-leer?: "))
                if sonda.re_leer_registros(n):
                    print(f"[OK] Puntero movido. Ahora use la opción 4.")
                else:
                    print("[!] La sonda rechazó el comando o no está conectada.")
            except ValueError: 
                print("[!] Ingrese un número entero válido.")

        elif op == "6":
            conf = input("\n¿Confirmar borrado total de memoria? (S/N): ")
            if conf.upper() == 'S':
                if sonda.inicializar_memoria(): 
                    print("[OK] Memoria borrada con éxito.")
                else:
                    print("[!] Error al intentar borrar la memoria.")

        elif op == "0":
            sonda.desconectar()
            print("\nSaliendo...")
            break

        input("\nPresione Enter para volver al menú...")

if __name__ == "__main__":
    ejecutar_app()