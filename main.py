import os
import datetime
from sonda_gs6200 import SondaGS6200

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def ejecutar_app():
    sonda = SondaGS6200() # Puedes quitar log_callback=print para un menú limpio
    
    while True:
        limpiar_pantalla()
        estado = "CONECTADA" if sonda.device else "DESCONECTADA"
        print(f"========================================")
        print(f"   PatrolApp - GESTIÓN GS-6200 [{estado}]")
        print(f"========================================")
        print("1. Conectar Sonda")
        print("2. Ver Info (ID y Hora actual)")
        print("3. Sincronizar reloj c/ hora de PC <Verificar la hora del PC>")
        print("4. DESCARGAR REGISTROS")
        print("5. Re-descargar registros ")
        print("6. Borrar Memoria Sonda <irreversible!>")
        print("0. Salir")
        print("----------------------------------------")
        
        op = input("Seleccione una opción: ")

        if op == "1":
            if sonda.conectar(): print("\n[OK] Sonda conectada correctamente.")
            else: print("\n[!] No se detectó la sonda.")

        elif op in ["2", "3", "4", "5", "6"] and not sonda.device:
            print("\n[!] Primero debe conectar la sonda (Opción 1).")

        elif op == "2":
            sid = sonda.obtener_id()
            rtc = sonda.obtener_rtc()
            print(f"\nID Dispositivo: {sid if sid else 'Error'}")
            print(f"Hora en Sonda: {rtc.strftime('%d/%m/%Y %H:%M:%S') if rtc else 'Error'}")

        elif op == "3":
            ahora = datetime.datetime.now()
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
                    print(f"{reg['tag']} {reg['fecha'].strftime('%d/%m/%Y %H:%M:%S')}")
            else:
                print("\n[?] No se encontraron registros nuevos o la memoria está vacía.")

        elif op == "5":
            try:
                n = int(input("\n¿Cuántos registros hacia atrás desea re-leer?: "))
                if sonda.re_leer_registros(n):
                    print(f"[OK] Puntero movido. Ahora use la opción 4 para descargar.")
                else:
                    print("[!] La sonda rechazó el comando.")
            except: print("[!] Ingrese un número entero válido.")

        elif op == "6":
            conf = input("\n¿Confirmar borrado total de memoria? (S/N): ")
            if conf.upper() == 'S':
                if sonda.inicializar_memoria(): 
                    print("[OK] Memoria borrada con éxito.")
                else:
                    print("[!] Error al intentar borrar la memoria.")

        elif op == "0":
            print("\nSaliendo...")
            break

        input("\nPresione Enter para volver al menú...")

if __name__ == "__main__":
    ejecutar_app()