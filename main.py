import os
import datetime
from sonda_gs6200 import SondaGS6200

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def ejecutar_app():
    sonda = SondaGS6200(log_callback=print)
    
    while True:
        limpiar_pantalla()
        estado = "CONECTADA" if sonda.device else "DESCONECTADA"
        print(f"========================================")
        print(f"   PatrolApp - GESTIÓN GS-6200 [{estado}]")
        print(f"========================================")
        print("1. Conectar Sonda")
        print("2. Ver Info (ID y Hora actual)")
        print("3. Sincronizar Hora con PC")
        print("4. DESCARGAR REGISTROS")
        print("5. Re-descargar registros (CMD 34)")
        print("6. Borrar Memoria Sonda (CMD 52)")
        print("0. Salir")
        print("----------------------------------------")
        
        op = input("Seleccione una opción: ")

        if op == "1":
            if sonda.conectar(): print("\n[OK] Sonda conectada correctamente.")
            else: print("\n[!] No se detectó la sonda.")

        elif op in ["2", "3", "4", "5", "6"] and not sonda.device:
            print("\n[!] Primero debe conectar la sonda (Opción 1).")

        elif op == "2":
            print(f"\nID Dispositivo: {sonda.obtener_id()}")
            rtc = sonda.obtener_rtc()
            print(f"Hora en Sonda: {rtc.strftime('%d/%m/%Y %H:%M:%S') if rtc else 'Error'}")

        elif op == "3":
            ahora = datetime.datetime.now()
            if sonda.enviar_hora(ahora):
                print(f"\n[OK] Hora sincronizada: {ahora.strftime('%H:%M:%S')}")

        elif op == "4":
            print("\nDescargando...")
            datos = sonda.descargar_datos()
            if datos:
                filename = f"descarga_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, "w") as f:
                    for r in datos:
                        f.write(f"{r['tag']} {r['fecha'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                print(f"[EXITO] {len(datos)} registros guardados en {filename}")
            else:
                print("[?] No hay registros nuevos.")

        elif op == "5":
            try:
                n = int(input("\n¿Cuántos registros hacia atrás desea re-leer?: "))
                if sonda.re_leer_registros(n):
                    print(f"[OK] Puntero movido. Ahora use la opción 4.")
            except: print("[!] Número inválido.")

        elif op == "6":
            conf = input("\n¿Confirmar borrado total de memoria? (S/N): ")
            if conf.upper() == 'S':
                if sonda.inicializar_memoria(): print("[OK] Memoria inicializada.")

        elif op == "0":
            break

        input("\nPresione Enter para volver al menú...")

if __name__ == "__main__":
    ejecutar_app()