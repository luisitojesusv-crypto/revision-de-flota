import sys
import sqlite3
import os
import pandas as pd
import shutil
import re
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QPushButton, QTableWidget, QTableWidgetItem,
                            QLabel, QLineEdit, QMessageBox, QDialog, QFormLayout,
                            QDialogButtonBox, QHeaderView, QFrame, QTextEdit,
                            QGroupBox, QInputDialog, QDateEdit, QFileDialog, QTabWidget,
                            QSplitter, QScrollArea, QComboBox, QGridLayout)
from PyQt6.QtCore import Qt, QDate, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QBrush, QPixmap, QPainter, QPen, QWheelEvent

# ============================================
# FUNCIÓN PARA RUTAS DE RECURSOS
# ============================================
def resource_path(relative_path):
    """Obtiene la ruta correcta para recursos"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ============================================
# CONFIGURACIÓN DE RUTAS DE IMÁGENES
# ============================================
# En macOS, usamos las rutas absolutas directamente
if sys.platform == "darwin":  # macOS
    RUTA_IMAGEN_AK = "/Users/potaito/Documents/mi entorno python/entorno/car-pickup-truck-vector-illustration-blueprint-70303672.webp"
    RUTA_IMAGEN_AG = "/Users/potaito/Documents/mi entorno python/entorno/camion-grua-perfeccionado.png"
    RUTA_IMAGEN_THA = "/Users/potaito/Documents/mi entorno python/entorno/telescopic-handler-sylwetka-telehandler-side-view-flat-vector-telescopic-handler-sylwetka-telehandler-side-view-flat-vector-164358965.webp"
else:  # Windows u otros
    RUTA_IMAGEN_AK = resource_path(os.path.join('imagenes', 'ak.webp'))
    RUTA_IMAGEN_AG = resource_path(os.path.join('imagenes', 'ag.png'))
    RUTA_IMAGEN_THA = resource_path(os.path.join('imagenes', 'tha.webp'))

# ============================================
# CLASE BACKUPMANAGER
# ============================================
class BackupManager:
    def __init__(self, db_path="vehiculos.db", backup_dir="backups", excel_dir="excel_automatico"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.excel_dir = excel_dir
        self.ultimo_backup = None

        for directorio in [backup_dir, excel_dir]:
            if not os.path.exists(directorio):
                os.makedirs(directorio)
                print(f"📁 Directorio creado: {directorio}")

    def hacer_backup(self, tipo="automático"):
        try:
            if not os.path.exists(self.db_path):
                return False, "La base de datos no existe"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}_{tipo}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            shutil.copy2(self.db_path, backup_path)
            self._guardar_excel_backup(timestamp, tipo)
            self._limpiar_backups_antiguos()

            self.ultimo_backup = backup_path
            return True, f"Backup guardado: {backup_filename}"

        except Exception as e:
            return False, f"Error al hacer backup: {str(e)}"

    def _guardar_excel_backup(self, timestamp, tipo):
        try:
            conn = sqlite3.connect(self.db_path)

            tablas = {
                'ak_vehiculos': 'AK - Vehículos',
                'ag_vehiculos': 'AG - Vehículos',
                'tha_vehiculos': 'THA - Vehículos',
                'registros_diarios_ak': 'AK - Registros Diarios',
                'registros_diarios_ag': 'AG - Registros Diarios',
                'registros_diarios_tha': 'THA - Registros Diarios',
                'danos_vehiculos': 'Daños de Vehículos',
                'checklist_vehiculos': 'Checklist de Vehículos'
            }

            excel_path = os.path.join(self.excel_dir, f"backup_{timestamp}_{tipo}.xlsx")

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for tabla, nombre_hoja in tablas.items():
                    try:
                        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
                        if not df.empty:
                            nombre_hoja = nombre_hoja[:31]
                            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                    except Exception as e:
                        print(f"  ⚠️ Error exportando {tabla}: {e}")

                resumen_data = []

                for tipo_veh in ['ak', 'ag', 'tha']:
                    df = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {tipo_veh}_vehiculos", conn)
                    total = df.iloc[0, 0] if not df.empty else 0
                    resumen_data.append([f"Total {tipo_veh.upper()}", total])

                df = pd.read_sql_query("SELECT COUNT(*) as total FROM checklist_vehiculos", conn)
                total_checklist = df.iloc[0, 0] if not df.empty else 0
                resumen_data.append(["Total Checklist", total_checklist])

                resumen_data.append(["Fecha Exportación", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

                df_resumen = pd.DataFrame(resumen_data, columns=['Concepto', 'Valor'])
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

            conn.close()
            print(f"✅ Excel guardado: {excel_path}")
        except Exception as e:
            print(f"⚠️ No se pudo guardar Excel backup: {e}")

    def _limpiar_backups_antiguos(self, mantener=20):
        try:
            backups = [f for f in os.listdir(self.backup_dir)
                      if f.startswith("backup_") and f.endswith('.db')]
            backups.sort(reverse=True)

            for old_backup in backups[mantener:]:
                try:
                    os.remove(os.path.join(self.backup_dir, old_backup))
                except:
                    pass

            excels = [f for f in os.listdir(self.excel_dir)
                     if f.startswith("backup_") and f.endswith('.xlsx')]
            excels.sort(reverse=True)

            for old_excel in excels[mantener:]:
                try:
                    os.remove(os.path.join(self.excel_dir, old_excel))
                except:
                    pass

        except Exception as e:
            print(f"⚠️ Error limpiando backups: {e}")

# ============================================
# CLASE BASEDATOSVEHICULOS
# ============================================
class BaseDatosVehiculos:
    def __init__(self, db_path="vehiculos.db"):
        self.db_path = db_path
        self.backup_manager = BackupManager(db_path)
        self.inicializar_bd()
        self.cargar_datos_iniciales()

    def inicializar_bd(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ak_vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ak_id TEXT UNIQUE NOT NULL,
                kilometraje_base INTEGER DEFAULT 0,
                kilometraje_actual INTEGER DEFAULT 0,
                kilometraje_acumulado INTEGER DEFAULT 0,
                contador_piso INTEGER DEFAULT 0,
                contador_agencia INTEGER DEFAULT 0,
                ultimo_mantenimiento_piso INTEGER DEFAULT 0,
                ultimo_mantenimiento_agencia INTEGER DEFAULT 0,
                ultimo_mantenimiento_piso_fecha TEXT,
                ultimo_mantenimiento_agencia_fecha TEXT,
                mantenimiento_piso_hecho BOOLEAN DEFAULT 0,
                fecha_registro TIMESTAMP,
                observaciones TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ag_vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ag_id TEXT UNIQUE NOT NULL,
                horas_base INTEGER DEFAULT 0,
                horas_actual INTEGER DEFAULT 0,
                horas_acumulado INTEGER DEFAULT 0,
                contador_piso INTEGER DEFAULT 0,
                contador_agencia INTEGER DEFAULT 0,
                ultimo_mantenimiento_piso INTEGER DEFAULT 0,
                ultimo_mantenimiento_agencia INTEGER DEFAULT 0,
                ultimo_mantenimiento_piso_fecha TEXT,
                ultimo_mantenimiento_agencia_fecha TEXT,
                mantenimiento_piso_hecho BOOLEAN DEFAULT 0,
                fecha_registro TIMESTAMP,
                observaciones TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tha_vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tha_id TEXT UNIQUE NOT NULL,
                horas_base INTEGER DEFAULT 0,
                horas_actual INTEGER DEFAULT 0,
                horas_acumulado INTEGER DEFAULT 0,
                contador_piso INTEGER DEFAULT 0,
                contador_agencia INTEGER DEFAULT 0,
                ultimo_mantenimiento_piso INTEGER DEFAULT 0,
                ultimo_mantenimiento_agencia INTEGER DEFAULT 0,
                ultimo_mantenimiento_piso_fecha TEXT,
                ultimo_mantenimiento_agencia_fecha TEXT,
                mantenimiento_piso_hecho BOOLEAN DEFAULT 0,
                fecha_registro TIMESTAMP,
                observaciones TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_diarios_ak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ak_id TEXT NOT NULL,
                fecha DATE NOT NULL,
                kilometraje_registrado INTEGER DEFAULT 0,
                kilometraje_actual INTEGER DEFAULT 0,
                tipo TEXT,
                observaciones TEXT,
                FOREIGN KEY (ak_id) REFERENCES ak_vehiculos(ak_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_diarios_ag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ag_id TEXT NOT NULL,
                fecha DATE NOT NULL,
                horas_registrado INTEGER DEFAULT 0,
                horas_actual INTEGER DEFAULT 0,
                tipo TEXT,
                observaciones TEXT,
                FOREIGN KEY (ag_id) REFERENCES ag_vehiculos(ag_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_diarios_tha (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tha_id TEXT NOT NULL,
                fecha DATE NOT NULL,
                horas_registrado INTEGER DEFAULT 0,
                horas_actual INTEGER DEFAULT 0,
                tipo TEXT,
                observaciones TEXT,
                FOREIGN KEY (tha_id) REFERENCES tha_vehiculos(tha_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS danos_vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehiculo_id TEXT NOT NULL,
                tipo_vehiculo TEXT NOT NULL,
                datos_danos TEXT NOT NULL,
                fecha_actualizacion TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checklist_vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehiculo_id TEXT NOT NULL,
                tipo_vehiculo TEXT NOT NULL,
                componente TEXT NOT NULL,
                estado TEXT DEFAULT 'OK',
                observaciones TEXT,
                fecha_actualizacion TIMESTAMP,
                UNIQUE(vehiculo_id, tipo_vehiculo, componente)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada")

    def cargar_datos_iniciales(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        datos_ak = [
            ("AK-42", 58092), ("AK-34", 15846), ("AK-36", 37056), ("AK-47", 114851),
            ("AK-46", 32675), ("AK-44", 6520), ("AK-45", 12624), ("AK-22", 48506),
            ("AK-37", 32104), ("AK-40", 22050), ("AK-10", 133933), ("AK-16", 92312),
            ("AK-01", 153681), ("AK-09", 158328), ("AK-41", 67979), ("AK-24", 51096),
            ("AK-14", 16104), ("AK-05", 154757), ("AK-25", 48939)
        ]

        cursor.execute("SELECT COUNT(*) FROM ak_vehiculos")
        if cursor.fetchone()[0] == 0:
            print("📦 Cargando datos iniciales de AKs...")
            for ak_id, km in datos_ak:
                try:
                    km_int = int(float(km))
                    cursor.execute('''
                        INSERT INTO ak_vehiculos
                        (ak_id, kilometraje_base, kilometraje_actual, kilometraje_acumulado,
                         contador_piso, contador_agencia, mantenimiento_piso_hecho, fecha_registro, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (ak_id, km_int, km_int, 0, 0, 0, 0, datetime.now().isoformat(), "Carga inicial"))
                except Exception as e:
                    print(f"Error insertando {ak_id}: {e}")

        ag_lista_original = [
            "AG-12", "AG-12", "AG-11", "AG-05", "AG-12", "AG-05", "AG-12", "AG-05", "AG-05", "AG-12",
            "AG-12", "AG-05", "AG-05", "AG-05", "AG-05", "AG-12", "AG-05", "AG-05", "AG-05", "AG-05",
            "AG-05", "AG-05", "AG-05", "AG-05", "AG-05", "AG-05", "AG-05", "AG-05", "AG-05", "AG-05",
            "AG-05", "AG-12", "AG-18", "AG-20", "AG-18", "AG-20", "AG-11", "AG-18", "AG-20", "AG-18",
            "AG-20", "AG-20", "AG-18", "AG-20", "AG-20", "AG-20", "AG-18", "AG-20", "AG-20", "AG-18",
            "AG-20", "AG-18", "AG-18", "AG-18", "AG-18", "AG-20", "AG-18", "AG-18", "AG-20", "AG-20",
            "AG-18", "AG-20", "AG-08", "AG-12", "AG-07", "AG-10 MOTOR 1", "AG-10 MOTOR 1", "AG-10 MOTOR 1",
            "AG-10 MOTOR 1", "AG-10 MOTOR 1", "AG-10 MOTOR 1", "AG-07", "AG-10", "AG-10", "AG-10", "AG-10",
            "AG-10", "AG-07", "AG-07", "AG-07", "AG-07", "AG-07", "AG-07"
        ]

        ag_ids_unicos = []
        for item in ag_lista_original:
            if item not in ag_ids_unicos and item != "1.2 ECONOMICO" and item:
                ag_ids_unicos.append(item)

        cursor.execute("SELECT COUNT(*) FROM ag_vehiculos")
        if cursor.fetchone()[0] == 0:
            print(f"📦 Cargando datos iniciales de AGs ({len(ag_ids_unicos)} únicos)...")
            for ag_id in ag_ids_unicos:
                try:
                    horas_base = 0
                    if ag_id == "AG-05":
                        horas_base = 1250
                    elif ag_id == "AG-07":
                        horas_base = 890
                    elif ag_id == "AG-08":
                        horas_base = 2340
                    elif "AG-10" in ag_id:
                        horas_base = 3120
                    elif ag_id == "AG-11":
                        horas_base = 456
                    elif ag_id == "AG-12":
                        horas_base = 1870
                    elif ag_id == "AG-18":
                        horas_base = 654
                    elif ag_id == "AG-20":
                        horas_base = 987

                    cursor.execute('''
                        INSERT INTO ag_vehiculos
                        (ag_id, horas_base, horas_actual, horas_acumulado,
                         contador_piso, contador_agencia, mantenimiento_piso_hecho, fecha_registro, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (ag_id, horas_base, horas_base, 0, 0, 0, 0, datetime.now().isoformat(), "Carga inicial"))
                except Exception as e:
                    print(f"Error insertando {ag_id}: {e}")

        tha_datos_raw = [
            ("THA-06", 3840), ("THA-17", 299), ("THA-12", 8031), ("THA-17", 300), ("THA-03", 7487),
            ("THA-03", 7528.3), ("THA-15", 8916.4), ("THA-10", 9477), ("THA-16", 1119.6), ("THA-17", 310),
            ("THA-12", 8047), ("THA-13", 2673), ("THA-16", 1130.3), ("THA-10", 9493), ("THA-17", 318),
            ("THA-13", 2681), ("THA-16", 1141.5), ("THA-10", 9500), ("THA-17", 326), ("THA-06", 3952),
            ("THA-16", 1665), ("THA-12", 8069), ("THA-10", 9517.8), ("THA-06", 3958), ("THA-12", 8069),
            ("THA-03", 7571), ("THA-10", 9526), ("THA-06", 3968), ("THA-06", 3968), ("THA-17", 343),
            ("THA-06", 3970), ("THA-10", 9522), ("THA-16", 1183.3), ("THA-06", 3963), ("THA-16", 1197),
            ("THA-10", 9534.9), ("THA-03", 7578), ("THA-12", 8080), ("THA-17", 343), ("THA-06", 3976),
            ("THA-16", 1209), ("THA-03", 7383), ("THA-10", 9542), ("THA-06", 3981), ("THA-13", 2749),
            ("THA-16", 1222), ("THA-06", 3988), ("THA-10", 4950), ("THA-03", 7588.5), ("THA-12", 8086),
            ("THA-10", 9548), ("THA-03", 7588), ("THA-03", 7593), ("THA-10", 9552.7), ("THA-17", 352),
            ("THA-13", 2770), ("THA-03", 7598.7), ("THA-12", 8096), ("THA-06", 4007), ("THA-03", 7598),
            ("THA-10", 9557.6), ("THA-16", 1245), ("THA-17", 366), ("THA-06", 4013), ("THA-03", 7603.7),
            ("THA-03", 7603), ("THA-12", 8103), ("THA-10", 9564.7), ("THA-17", 381), ("THA-10", 9660),
            ("THA-12", 8113), ("THA-13", 2785), ("THA-16", 1264), ("THA-06", 4017), ("THA-16", 1264),
            ("THA-03", 7606), ("THA-10", 9573.1), ("THA-17", 387), ("THA-03", 7611.3), ("THA-06", 4026),
            ("THA-03", 7611), ("THA-10", 9583.7), ("THA-10", 9598.1), ("THA-10", 9582), ("THA-10", 9608),
            ("THA-17", 429), ("THA-10", 9618.8), ("THA-10", 9636)
        ]

        tha_maximos = {}
        for tha_id, valor in tha_datos_raw:
            try:
                if isinstance(valor, str):
                    if '-' in valor:
                        partes = valor.replace(' ', '').split('-')
                        valor = float(partes[-1])
                    else:
                        valor = float(valor)
                else:
                    valor = float(valor)
            except:
                valor = 0

            if tha_id not in tha_maximos or valor > tha_maximos[tha_id]:
                tha_maximos[tha_id] = int(valor)

        tha_ids_unicos = sorted(list(tha_maximos.keys()))

        cursor.execute("SELECT COUNT(*) FROM tha_vehiculos")
        if cursor.fetchone()[0] == 0:
            print(f"📦 Cargando datos iniciales de THA ({len(tha_ids_unicos)} únicos)...")
            for tha_id in tha_ids_unicos:
                try:
                    horas_base = tha_maximos[tha_id]
                    cursor.execute('''
                        INSERT INTO tha_vehiculos
                        (tha_id, horas_base, horas_actual, horas_acumulado,
                         contador_piso, contador_agencia, mantenimiento_piso_hecho, fecha_registro, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (tha_id, horas_base, horas_base, 0, 0, 0, 0, datetime.now().isoformat(), "Carga inicial"))
                    print(f"  ✅ Insertado: {tha_id} con {horas_base} horas")
                except Exception as e:
                    print(f"Error insertando {tha_id}: {e}")

        conn.commit()
        conn.close()
        print("✅ Datos iniciales cargados")

# ============================================
# CLASE EXPORTADOREXCEL
# ============================================
class ExportadorExcel:
    def __init__(self, db_path="vehiculos.db"):
        self.db_path = db_path

    def exportar_todo(self, file_path=None):
        try:
            conn = sqlite3.connect(self.db_path)

            if file_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = f"exportacion_automatica_{timestamp}.xlsx"

            tablas = {
                'ak_vehiculos': 'AK - Vehículos',
                'ag_vehiculos': 'AG - Vehículos',
                'tha_vehiculos': 'THA - Vehículos',
                'registros_diarios_ak': 'AK - Registros Diarios',
                'registros_diarios_ag': 'AG - Registros Diarios',
                'registros_diarios_tha': 'THA - Registros Diarios',
                'danos_vehiculos': 'Daños de Vehículos',
                'checklist_vehiculos': 'Checklist de Vehículos'
            }

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for tabla, nombre_hoja in tablas.items():
                    try:
                        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
                        if not df.empty:
                            nombre_hoja = nombre_hoja[:31]
                            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
                            print(f"  ✅ Exportada tabla: {tabla} ({len(df)} registros)")
                    except Exception as e:
                        print(f"  ⚠️ Error exportando {tabla}: {e}")

                resumen_data = []

                for tipo in ['ak', 'ag', 'tha']:
                    df = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {tipo}_vehiculos", conn)
                    total = df.iloc[0, 0] if not df.empty else 0
                    resumen_data.append([f"Total {tipo.upper()}", total])

                for tipo in ['ak', 'ag', 'tha']:
                    df = pd.read_sql_query(f"SELECT COUNT(*) as total FROM registros_diarios_{tipo}", conn)
                    total = df.iloc[0, 0] if not df.empty else 0
                    resumen_data.append([f"Registros {tipo.upper()}", total])

                df = pd.read_sql_query("SELECT COUNT(*) as total FROM danos_vehiculos", conn)
                total_danos = df.iloc[0, 0] if not df.empty else 0
                resumen_data.append(["Total Daños", total_danos])

                df = pd.read_sql_query("SELECT COUNT(*) as total FROM checklist_vehiculos", conn)
                total_checklist = df.iloc[0, 0] if not df.empty else 0
                resumen_data.append(["Total Checklist", total_checklist])

                df_estados = pd.read_sql_query("""
                    SELECT estado, COUNT(*) as cantidad
                    FROM checklist_vehiculos
                    GROUP BY estado
                """, conn)

                for _, row in df_estados.iterrows():
                    resumen_data.append([f"Checklist {row['estado']}", row['cantidad']])

                resumen_data.append(["Fecha Exportación", datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

                df_resumen = pd.DataFrame(resumen_data, columns=['Concepto', 'Valor'])
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)

            conn.close()
            return True, f"Archivo guardado: {os.path.basename(file_path)}", file_path

        except Exception as e:
            return False, f"Error al exportar: {str(e)}", None

# ============================================
# GESTIÓN AK
# ============================================
class GestionAK:
    def __init__(self, db_path="vehiculos.db"):
        self.db_path = db_path

    def obtener_todos(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, ak_id, kilometraje_base, kilometraje_actual,
                   kilometraje_acumulado, contador_piso, contador_agencia,
                   ultimo_mantenimiento_piso_fecha, ultimo_mantenimiento_agencia_fecha,
                   mantenimiento_piso_hecho
            FROM ak_vehiculos
            ORDER BY ak_id
        ''')
        datos = cursor.fetchall()
        conn.close()
        return datos

    def buscar(self, termino):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, ak_id, kilometraje_base, kilometraje_actual,
                   kilometraje_acumulado, contador_piso, contador_agencia,
                   ultimo_mantenimiento_piso_fecha, ultimo_mantenimiento_agencia_fecha,
                   mantenimiento_piso_hecho
            FROM ak_vehiculos
            WHERE ak_id LIKE ?
            ORDER BY ak_id
        ''', (f'%{termino}%',))
        datos = cursor.fetchall()
        conn.close()
        return datos

    def obtener_historial(self, ak_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha, kilometraje_registrado, kilometraje_actual, tipo, observaciones
            FROM registros_diarios_ak
            WHERE ak_id = ?
            ORDER BY fecha DESC
            LIMIT 50
        ''', (ak_id,))
        historial = cursor.fetchall()
        conn.close()
        return historial

    def agregar(self, ak_id, kilometraje_inicial=0, observaciones=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO ak_vehiculos
                (ak_id, kilometraje_base, kilometraje_actual, kilometraje_acumulado,
                 contador_piso, contador_agencia, mantenimiento_piso_hecho, fecha_registro, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ak_id, kilometraje_inicial, kilometraje_inicial, 0, 0, 0, 0, datetime.now().isoformat(), observaciones))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def eliminar(self, ak_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ak_vehiculos WHERE ak_id = ?', (ak_id,))
        cursor.execute('DELETE FROM registros_diarios_ak WHERE ak_id = ?', (ak_id,))
        conn.commit()
        conn.close()
        return True

    def registrar_kilometraje(self, ak_id, km_nuevos, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT kilometraje_actual, kilometraje_acumulado, contador_piso, contador_agencia,
                   mantenimiento_piso_hecho
            FROM ak_vehiculos
            WHERE ak_id = ?
        ''', (ak_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False, None, None, "AK no encontrado"

        km_actual, km_acumulado, cont_piso, cont_agencia, manto_piso_hecho = resultado

        nuevo_km_actual = km_actual + km_nuevos
        nuevo_km_acumulado = km_acumulado + km_nuevos

        if manto_piso_hecho:
            nuevo_cont_piso = cont_piso
        else:
            nuevo_cont_piso = cont_piso + km_nuevos

        nuevo_cont_agencia = cont_agencia + km_nuevos

        requiere_manto_piso = not manto_piso_hecho and nuevo_cont_piso >= 250
        requiere_manto_agencia = nuevo_cont_agencia >= 500

        cursor.execute('''
            UPDATE ak_vehiculos
            SET kilometraje_actual = ?,
                kilometraje_acumulado = ?,
                contador_piso = ?,
                contador_agencia = ?
            WHERE ak_id = ?
        ''', (nuevo_km_actual, nuevo_km_acumulado, nuevo_cont_piso, nuevo_cont_agencia, ak_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ak
            (ak_id, fecha, kilometraje_registrado, kilometraje_actual, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (ak_id, fecha.isoformat(), km_nuevos, nuevo_km_actual, observaciones))

        conn.commit()
        conn.close()

        return True, requiere_manto_piso, requiere_manto_agencia, None

    def registrar_mantenimiento_piso(self, ak_id, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT kilometraje_actual, contador_piso
            FROM ak_vehiculos
            WHERE ak_id = ?
        ''', (ak_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False

        km_actual, cont_piso = resultado

        cursor.execute('''
            UPDATE ak_vehiculos
            SET mantenimiento_piso_hecho = 1,
                ultimo_mantenimiento_piso = ?,
                ultimo_mantenimiento_piso_fecha = ?
            WHERE ak_id = ?
        ''', (km_actual, fecha.isoformat(), ak_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ak
            (ak_id, fecha, kilometraje_registrado, kilometraje_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ak_id, fecha.isoformat(), 0, km_actual, "MANTENIMIENTO_PISO",
              f"✅ Mantenimiento PISO realizado - Contador congelado en {cont_piso} - {observaciones}"))

        conn.commit()
        conn.close()
        return True

    def registrar_mantenimiento_agencia(self, ak_id, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT kilometraje_actual, contador_piso, contador_agencia
            FROM ak_vehiculos
            WHERE ak_id = ?
        ''', (ak_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False

        km_actual, cont_piso, cont_agencia = resultado

        cursor.execute('''
            UPDATE ak_vehiculos
            SET contador_piso = 0,
                contador_agencia = 0,
                mantenimiento_piso_hecho = 0,
                ultimo_mantenimiento_agencia = ?,
                ultimo_mantenimiento_agencia_fecha = ?,
                ultimo_mantenimiento_piso = ?,
                ultimo_mantenimiento_piso_fecha = ?
            WHERE ak_id = ?
        ''', (km_actual, fecha.isoformat(), km_actual, fecha.isoformat(), ak_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ak
            (ak_id, fecha, kilometraje_registrado, kilometraje_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ak_id, fecha.isoformat(), 0, km_actual, "MANTENIMIENTO_AGENCIA",
              f"🏢 Mantenimiento AGENCIA realizado - Contadores reiniciados (Piso:{cont_piso}, Agencia:{cont_agencia}) - Reactivado Piso - {observaciones}"))

        conn.commit()
        conn.close()
        return True

    def editar_kilometraje(self, ak_id, nuevo_kilometraje, observaciones=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT kilometraje_actual FROM ak_vehiculos WHERE ak_id = ?', (ak_id,))
        resultado = cursor.fetchone()
        if not resultado:
            conn.close()
            return False, "AK no encontrado"

        km_actual = resultado[0]

        cursor.execute('''
            UPDATE ak_vehiculos
            SET kilometraje_actual = ?
            WHERE ak_id = ?
        ''', (nuevo_kilometraje, ak_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ak
            (ak_id, fecha, kilometraje_registrado, kilometraje_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ak_id, datetime.now().date().isoformat(), nuevo_kilometraje - km_actual,
              nuevo_kilometraje, "CORRECCIÓN", observaciones))

        conn.commit()
        conn.close()
        return True, f"Kilometraje corregido de {km_actual:,} a {nuevo_kilometraje:,} km"

# ============================================
# GESTIÓN AG
# ============================================
class GestionAG:
    def __init__(self, db_path="vehiculos.db"):
        self.db_path = db_path

    def obtener_todos(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, ag_id, horas_base, horas_actual,
                   horas_acumulado, contador_piso, contador_agencia,
                   ultimo_mantenimiento_piso_fecha, ultimo_mantenimiento_agencia_fecha,
                   mantenimiento_piso_hecho
            FROM ag_vehiculos
            ORDER BY ag_id
        ''')
        datos = cursor.fetchall()
        conn.close()
        return datos

    def buscar(self, termino):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, ag_id, horas_base, horas_actual,
                   horas_acumulado, contador_piso, contador_agencia,
                   ultimo_mantenimiento_piso_fecha, ultimo_mantenimiento_agencia_fecha,
                   mantenimiento_piso_hecho
            FROM ag_vehiculos
            WHERE ag_id LIKE ?
            ORDER BY ag_id
        ''', (f'%{termino}%',))
        datos = cursor.fetchall()
        conn.close()
        return datos

    def obtener_historial(self, ag_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha, horas_registrado, horas_actual, tipo, observaciones
            FROM registros_diarios_ag
            WHERE ag_id = ?
            ORDER BY fecha DESC
            LIMIT 50
        ''', (ag_id,))
        historial = cursor.fetchall()
        conn.close()
        return historial

    def agregar(self, ag_id, horas_iniciales=0, observaciones=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO ag_vehiculos
                (ag_id, horas_base, horas_actual, horas_acumulado,
                 contador_piso, contador_agencia, mantenimiento_piso_hecho, fecha_registro, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ag_id, horas_iniciales, horas_iniciales, 0, 0, 0, 0, datetime.now().isoformat(), observaciones))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def eliminar(self, ag_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ag_vehiculos WHERE ag_id = ?', (ag_id,))
        cursor.execute('DELETE FROM registros_diarios_ag WHERE ag_id = ?', (ag_id,))
        conn.commit()
        conn.close()
        return True

    def registrar_horas(self, ag_id, horas_nuevas, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT horas_actual, horas_acumulado, contador_piso, contador_agencia,
                   mantenimiento_piso_hecho
            FROM ag_vehiculos
            WHERE ag_id = ?
        ''', (ag_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False, None, None, "AG no encontrado"

        horas_actual, horas_acumulado, cont_piso, cont_agencia, manto_piso_hecho = resultado

        nuevas_horas_actual = horas_actual + horas_nuevas
        nuevas_horas_acumulado = horas_acumulado + horas_nuevas

        if manto_piso_hecho:
            nuevo_cont_piso = cont_piso
        else:
            nuevo_cont_piso = cont_piso + horas_nuevas

        nuevo_cont_agencia = cont_agencia + horas_nuevas

        requiere_manto_piso = not manto_piso_hecho and nuevo_cont_piso >= 250
        requiere_manto_agencia = nuevo_cont_agencia >= 500

        cursor.execute('''
            UPDATE ag_vehiculos
            SET horas_actual = ?,
                horas_acumulado = ?,
                contador_piso = ?,
                contador_agencia = ?
            WHERE ag_id = ?
        ''', (nuevas_horas_actual, nuevas_horas_acumulado, nuevo_cont_piso, nuevo_cont_agencia, ag_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ag
            (ag_id, fecha, horas_registrado, horas_actual, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (ag_id, fecha.isoformat(), horas_nuevas, nuevas_horas_actual, observaciones))

        conn.commit()
        conn.close()

        return True, requiere_manto_piso, requiere_manto_agencia, None

    def registrar_mantenimiento_piso(self, ag_id, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT horas_actual, contador_piso
            FROM ag_vehiculos
            WHERE ag_id = ?
        ''', (ag_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False

        horas_actual, cont_piso = resultado

        cursor.execute('''
            UPDATE ag_vehiculos
            SET mantenimiento_piso_hecho = 1,
                ultimo_mantenimiento_piso = ?,
                ultimo_mantenimiento_piso_fecha = ?
            WHERE ag_id = ?
        ''', (horas_actual, fecha.isoformat(), ag_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ag
            (ag_id, fecha, horas_registrado, horas_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ag_id, fecha.isoformat(), 0, horas_actual, "MANTENIMIENTO_PISO",
              f"✅ Mantenimiento PISO realizado - Contador congelado en {cont_piso} - {observaciones}"))

        conn.commit()
        conn.close()
        return True

    def registrar_mantenimiento_agencia(self, ag_id, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT horas_actual, contador_piso, contador_agencia
            FROM ag_vehiculos
            WHERE ag_id = ?
        ''', (ag_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False

        horas_actual, cont_piso, cont_agencia = resultado

        cursor.execute('''
            UPDATE ag_vehiculos
            SET contador_piso = 0,
                contador_agencia = 0,
                mantenimiento_piso_hecho = 0,
                ultimo_mantenimiento_agencia = ?,
                ultimo_mantenimiento_agencia_fecha = ?,
                ultimo_mantenimiento_piso = ?,
                ultimo_mantenimiento_piso_fecha = ?
            WHERE ag_id = ?
        ''', (horas_actual, fecha.isoformat(), horas_actual, fecha.isoformat(), ag_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ag
            (ag_id, fecha, horas_registrado, horas_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ag_id, fecha.isoformat(), 0, horas_actual, "MANTENIMIENTO_AGENCIA",
              f"🏢 Mantenimiento AGENCIA realizado - Contadores reiniciados (Piso:{cont_piso}, Agencia:{cont_agencia}) - Reactivado Piso - {observaciones}"))

        conn.commit()
        conn.close()
        return True

    def editar_horas(self, ag_id, nuevas_horas, observaciones=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT horas_actual FROM ag_vehiculos WHERE ag_id = ?', (ag_id,))
        resultado = cursor.fetchone()
        if not resultado:
            conn.close()
            return False, "AG no encontrado"

        horas_actual = resultado[0]

        cursor.execute('''
            UPDATE ag_vehiculos
            SET horas_actual = ?
            WHERE ag_id = ?
        ''', (nuevas_horas, ag_id))

        cursor.execute('''
            INSERT INTO registros_diarios_ag
            (ag_id, fecha, horas_registrado, horas_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ag_id, datetime.now().date().isoformat(), nuevas_horas - horas_actual,
              nuevas_horas, "CORRECCIÓN", observaciones))

        conn.commit()
        conn.close()
        return True, f"Horas corregidas de {horas_actual:,} a {nuevas_horas:,} horas"

# ============================================
# GESTIÓN THA
# ============================================
class GestionTHA:
    def __init__(self, db_path="vehiculos.db"):
        self.db_path = db_path

    def obtener_todos(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, tha_id, horas_base, horas_actual,
                   horas_acumulado, contador_piso, contador_agencia,
                   ultimo_mantenimiento_piso_fecha, ultimo_mantenimiento_agencia_fecha,
                   mantenimiento_piso_hecho
            FROM tha_vehiculos
            ORDER BY tha_id
        ''')
        datos = cursor.fetchall()
        conn.close()
        return datos

    def buscar(self, termino):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, tha_id, horas_base, horas_actual,
                   horas_acumulado, contador_piso, contador_agencia,
                   ultimo_mantenimiento_piso_fecha, ultimo_mantenimiento_agencia_fecha,
                   mantenimiento_piso_hecho
            FROM tha_vehiculos
            WHERE tha_id LIKE ?
            ORDER BY tha_id
        ''', (f'%{termino}%',))
        datos = cursor.fetchall()
        conn.close()
        return datos

    def obtener_historial(self, tha_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha, horas_registrado, horas_actual, tipo, observaciones
            FROM registros_diarios_tha
            WHERE tha_id = ?
            ORDER BY fecha DESC
            LIMIT 50
        ''', (tha_id,))
        historial = cursor.fetchall()
        conn.close()
        return historial

    def agregar(self, tha_id, horas_iniciales=0, observaciones=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO tha_vehiculos
                (tha_id, horas_base, horas_actual, horas_acumulado,
                 contador_piso, contador_agencia, mantenimiento_piso_hecho, fecha_registro, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tha_id, horas_iniciales, horas_iniciales, 0, 0, 0, 0, datetime.now().isoformat(), observaciones))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def eliminar(self, tha_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tha_vehiculos WHERE tha_id = ?', (tha_id,))
        cursor.execute('DELETE FROM registros_diarios_tha WHERE tha_id = ?', (tha_id,))
        conn.commit()
        conn.close()
        return True

    def registrar_horas(self, tha_id, horas_nuevas, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT horas_actual, horas_acumulado, contador_piso, contador_agencia,
                   mantenimiento_piso_hecho
            FROM tha_vehiculos
            WHERE tha_id = ?
        ''', (tha_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False, None, None, "THA no encontrado"

        horas_actual, horas_acumulado, cont_piso, cont_agencia, manto_piso_hecho = resultado

        nuevas_horas_actual = horas_actual + horas_nuevas
        nuevas_horas_acumulado = horas_acumulado + horas_nuevas

        if manto_piso_hecho:
            nuevo_cont_piso = cont_piso
        else:
            nuevo_cont_piso = cont_piso + horas_nuevas

        nuevo_cont_agencia = cont_agencia + horas_nuevas

        requiere_manto_piso = not manto_piso_hecho and nuevo_cont_piso >= 250
        requiere_manto_agencia = nuevo_cont_agencia >= 500

        cursor.execute('''
            UPDATE tha_vehiculos
            SET horas_actual = ?,
                horas_acumulado = ?,
                contador_piso = ?,
                contador_agencia = ?
            WHERE tha_id = ?
        ''', (nuevas_horas_actual, nuevas_horas_acumulado, nuevo_cont_piso, nuevo_cont_agencia, tha_id))

        cursor.execute('''
            INSERT INTO registros_diarios_tha
            (tha_id, fecha, horas_registrado, horas_actual, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (tha_id, fecha.isoformat(), horas_nuevas, nuevas_horas_actual, observaciones))

        conn.commit()
        conn.close()

        return True, requiere_manto_piso, requiere_manto_agencia, None

    def registrar_mantenimiento_piso(self, tha_id, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT horas_actual, contador_piso
            FROM tha_vehiculos
            WHERE tha_id = ?
        ''', (tha_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False

        horas_actual, cont_piso = resultado

        cursor.execute('''
            UPDATE tha_vehiculos
            SET mantenimiento_piso_hecho = 1,
                ultimo_mantenimiento_piso = ?,
                ultimo_mantenimiento_piso_fecha = ?
            WHERE tha_id = ?
        ''', (horas_actual, fecha.isoformat(), tha_id))

        cursor.execute('''
            INSERT INTO registros_diarios_tha
            (tha_id, fecha, horas_registrado, horas_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tha_id, fecha.isoformat(), 0, horas_actual, "MANTENIMIENTO_PISO",
              f"✅ Mantenimiento PISO realizado - Contador congelado en {cont_piso} - {observaciones}"))

        conn.commit()
        conn.close()
        return True

    def registrar_mantenimiento_agencia(self, tha_id, fecha=None, observaciones=""):
        if fecha is None:
            fecha = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT horas_actual, contador_piso, contador_agencia
            FROM tha_vehiculos
            WHERE tha_id = ?
        ''', (tha_id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return False

        horas_actual, cont_piso, cont_agencia = resultado

        cursor.execute('''
            UPDATE tha_vehiculos
            SET contador_piso = 0,
                contador_agencia = 0,
                mantenimiento_piso_hecho = 0,
                ultimo_mantenimiento_agencia = ?,
                ultimo_mantenimiento_agencia_fecha = ?,
                ultimo_mantenimiento_piso = ?,
                ultimo_mantenimiento_piso_fecha = ?
            WHERE tha_id = ?
        ''', (horas_actual, fecha.isoformat(), horas_actual, fecha.isoformat(), tha_id))

        cursor.execute('''
            INSERT INTO registros_diarios_tha
            (tha_id, fecha, horas_registrado, horas_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tha_id, fecha.isoformat(), 0, horas_actual, "MANTENIMIENTO_AGENCIA",
              f"🏢 Mantenimiento AGENCIA realizado - Contadores reiniciados (Piso:{cont_piso}, Agencia:{cont_agencia}) - Reactivado Piso - {observaciones}"))

        conn.commit()
        conn.close()
        return True

    def editar_horas(self, tha_id, nuevas_horas, observaciones=""):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT horas_actual FROM tha_vehiculos WHERE tha_id = ?', (tha_id,))
        resultado = cursor.fetchone()
        if not resultado:
            conn.close()
            return False, "THA no encontrado"

        horas_actual = resultado[0]

        cursor.execute('''
            UPDATE tha_vehiculos
            SET horas_actual = ?
            WHERE tha_id = ?
        ''', (nuevas_horas, tha_id))

        cursor.execute('''
            INSERT INTO registros_diarios_tha
            (tha_id, fecha, horas_registrado, horas_actual, tipo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tha_id, datetime.now().date().isoformat(), nuevas_horas - horas_actual,
              nuevas_horas, "CORRECCIÓN", observaciones))

        conn.commit()
        conn.close()
        return True, f"Horas corregidas de {horas_actual:,} a {nuevas_horas:,} horas"

# ============================================
# DIÁLOGOS AK
# ============================================
class DialogoRegistrarKilometrajeAK(QDialog):
    def __init__(self, ak_id, km_actual, cont_piso, cont_agencia, manto_piso_hecho, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Registrar Kilometraje - {ak_id}")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        info_group = QGroupBox("Información Actual")
        info_layout = QFormLayout()

        self.ak_label = QLabel(ak_id)
        self.ak_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        info_layout.addRow("AK:", self.ak_label)

        self.km_actual_label = QLabel(f"{km_actual:,} km")
        self.km_actual_label.setStyleSheet("font-size: 14px;")
        info_layout.addRow("Kilometraje actual:", self.km_actual_label)

        if manto_piso_hecho:
            self.cont_piso_label = QLabel("✅ MANTENIMIENTO PISO HECHO")
            self.cont_piso_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        else:
            if cont_piso >= 250:
                piso_color = "#f38ba8"
                piso_text = f"🔴 REQUIERE MANTENIMIENTO"
            elif cont_piso >= 225:
                piso_color = "#f9e2af"
                piso_text = f"🟡 PRÓXIMO PISO ({cont_piso}/250)"
            elif cont_piso >= 200:
                piso_color = "#a6e3a1"
                piso_text = f"🟢 PRÓXIMO PISO ({cont_piso}/250)"
            else:
                piso_color = "#a6e3a1"
                piso_text = f"{cont_piso}/250 km"

            self.cont_piso_label = QLabel(piso_text)
            self.cont_piso_label.setStyleSheet(f"color: {piso_color}; font-weight: bold;")

        info_layout.addRow("Piso:", self.cont_piso_label)

        if cont_agencia >= 500:
            agencia_color = "#f38ba8"
            agencia_text = f"🔴 REQUIERE MANTENIMIENTO"
        elif cont_agencia >= 450:
            agencia_color = "#fab387"
            agencia_text = f"🟠 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        elif cont_agencia >= 400:
            agencia_color = "#f9e2af"
            agencia_text = f"🟡 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        elif cont_agencia >= 350:
            agencia_color = "#a6e3a1"
            agencia_text = f"🟢 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        else:
            agencia_color = "#a6e3a1"
            agencia_text = f"{cont_agencia}/500 km"

        self.cont_agencia_label = QLabel(agencia_text)
        self.cont_agencia_label.setStyleSheet(f"color: {agencia_color}; font-weight: bold;")
        info_layout.addRow("Agencia:", self.cont_agencia_label)

        info_group.setLayout(info_layout)
        layout.addRow(info_group)

        registro_group = QGroupBox("Nuevo Registro")
        registro_layout = QFormLayout()

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        self.fecha.setEnabled(False)
        registro_layout.addRow("Fecha (hoy):", self.fecha)

        self.km_nuevos = QLineEdit()
        self.km_nuevos.setPlaceholderText("Ej: 8, 15, 25...")
        self.km_nuevos.textChanged.connect(self.actualizar_preview)
        registro_layout.addRow("Km a registrar:", self.km_nuevos)

        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)

        self.preview_label = QLabel("Nuevo total: --- km")
        self.preview_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        preview_layout.addWidget(self.preview_label)

        self.preview_piso = QLabel("Nuevo progreso Piso: ---")
        self.preview_agencia = QLabel("Nuevo progreso Agencia: ---")
        preview_layout.addWidget(self.preview_piso)
        preview_layout.addWidget(self.preview_agencia)

        registro_layout.addRow("", self.preview_frame)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(80)
        self.observaciones.setPlaceholderText("Observaciones (opcional)")
        registro_layout.addRow("Observaciones:", self.observaciones)

        registro_group.setLayout(registro_layout)
        layout.addRow(registro_group)

        self.km_actual_valor = km_actual
        self.cont_piso_valor = cont_piso
        self.cont_agencia_valor = cont_agencia
        self.manto_piso_hecho = manto_piso_hecho

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def actualizar_preview(self):
        try:
            km_nuevos = int(self.km_nuevos.text() or 0)
            nuevo_total = self.km_actual_valor + km_nuevos
            self.preview_label.setText(f"Nuevo total: {nuevo_total:,} km")

            if self.manto_piso_hecho:
                self.preview_piso.setText("Nuevo progreso Piso: ✅ MANTENIMIENTO HECHO (congelado)")
                self.preview_piso.setStyleSheet("color: #89b4fa;")
            else:
                nuevo_piso = self.cont_piso_valor + km_nuevos
                if nuevo_piso >= 250:
                    piso_color = "#f38ba8"
                    piso_text = f"🔴 REQUIERE MANTENIMIENTO ({nuevo_piso}/250)"
                elif nuevo_piso >= 225:
                    piso_color = "#f9e2af"
                    piso_text = f"🟡 PRÓXIMO PISO ({nuevo_piso}/250)"
                elif nuevo_piso >= 200:
                    piso_color = "#a6e3a1"
                    piso_text = f"🟢 PRÓXIMO PISO ({nuevo_piso}/250)"
                else:
                    piso_color = "#a6e3a1"
                    piso_text = f"{nuevo_piso}/250 km"

                self.preview_piso.setText(f"Nuevo progreso Piso: {piso_text}")
                self.preview_piso.setStyleSheet(f"color: {piso_color};")

            nuevo_agencia = self.cont_agencia_valor + km_nuevos
            if nuevo_agencia >= 500:
                agencia_color = "#f38ba8"
                agencia_text = f"🔴 REQUIERE MANTENIMIENTO ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 450:
                agencia_color = "#fab387"
                agencia_text = f"🟠 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 400:
                agencia_color = "#f9e2af"
                agencia_text = f"🟡 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 350:
                agencia_color = "#a6e3a1"
                agencia_text = f"🟢 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            else:
                agencia_color = "#a6e3a1"
                agencia_text = f"{nuevo_agencia}/500 km"

            self.preview_agencia.setText(f"Nuevo progreso Agencia: {agencia_text}")
            self.preview_agencia.setStyleSheet(f"color: {agencia_color};")

        except:
            self.preview_label.setText("Nuevo total: --- km")
            self.preview_piso.setText("Nuevo progreso Piso: ---")
            self.preview_agencia.setText("Nuevo progreso Agencia: ---")

    def get_data(self):
        try:
            return {
                'km_nuevos': int(self.km_nuevos.text()),
                'fecha': self.fecha.date().toPyDate(),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
            return None

class DialogoMantenimientoPisoAK(QDialog):
    def __init__(self, ak_id, contador_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mantenimiento Piso - {ak_id}")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        info_label = QLabel(f"AK: {ak_id}")
        info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        layout.addRow(info_label)

        layout.addRow(QLabel("✅ Mantenimiento de PISO completado"))
        layout.addRow(QLabel(f"Contador actual: {contador_actual}/250 km"))
        layout.addRow(QLabel("Se marcará como HECHO y se congelará el contador"))
        layout.addRow(QLabel("hasta el próximo mantenimiento de AGENCIA."))

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        layout.addRow("Fecha:", self.fecha)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones del mantenimiento...")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'fecha': self.fecha.date().toPyDate(),
            'observaciones': self.observaciones.toPlainText()
        }

class DialogoMantenimientoAgenciaAK(QDialog):
    def __init__(self, ak_id, contador_piso, contador_agencia, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mantenimiento Agencia - {ak_id}")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        info_label = QLabel(f"AK: {ak_id}")
        info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        layout.addRow(info_label)

        layout.addRow(QLabel("🏢 Mantenimiento de AGENCIA completado"))
        layout.addRow(QLabel(f"Contador Piso: {contador_piso}/250 km"))
        layout.addRow(QLabel(f"Contador Agencia: {contador_agencia}/500 km"))
        layout.addRow(QLabel("⚠️ Se reiniciarán AMBOS contadores a 0"))

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        layout.addRow("Fecha:", self.fecha)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones del mantenimiento...")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'fecha': self.fecha.date().toPyDate(),
            'observaciones': self.observaciones.toPlainText()
        }

class DialogoEditarKilometrajeAK(QDialog):
    def __init__(self, ak_id, km_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Kilometraje - {ak_id}")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        layout.addRow(QLabel(f"AK: {ak_id}"))
        layout.addRow(QLabel(f"Kilometraje actual: {km_actual:,} km"))

        self.nuevo_km = QLineEdit()
        self.nuevo_km.setPlaceholderText("Ingrese el kilometraje correcto")
        self.nuevo_km.setText(str(km_actual))
        layout.addRow("Nuevo kilometraje:", self.nuevo_km)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(80)
        self.observaciones.setPlaceholderText("Motivo de la corrección...")
        layout.addRow("Motivo:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        try:
            return {
                'nuevo_km': int(self.nuevo_km.text()),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
            return None

class DialogoAgregarAK(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Nuevo AK")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.ak_id = QLineEdit()
        self.ak_id.setPlaceholderText("Ej: AK-01")
        layout.addRow("ID del AK:", self.ak_id)

        self.kilometraje = QLineEdit()
        self.kilometraje.setPlaceholderText("Kilometraje inicial")
        layout.addRow("Kilometraje base:", self.kilometraje)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones (opcional)")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        try:
            return {
                'ak_id': self.ak_id.text().strip().upper(),
                'kilometraje': int(self.kilometraje.text() or 0),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido para kilometraje")
            return None

class DialogoHistorialAK(QDialog):
    def __init__(self, ak_id, historial, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Historial - {ak_id}")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        title = QLabel(f"📋 Historial de Registros - {ak_id}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(title)

        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["Fecha", "Km Registrados", "Km Total", "Tipo", "Observaciones"])
        tabla.horizontalHeader().setStretchLastSection(True)

        tabla.setRowCount(len(historial))
        for i, row in enumerate(historial):
            for j, val in enumerate(row):
                if j == 1 or j == 2:
                    item = QTableWidgetItem(f"{val:,}" if val else "0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                else:
                    item = QTableWidgetItem(str(val))
                tabla.setItem(i, j, item)

        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

# ============================================
# DIÁLOGOS AG
# ============================================
class DialogoRegistrarHorasAG(QDialog):
    def __init__(self, ag_id, horas_actual, cont_piso, cont_agencia, manto_piso_hecho, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Registrar Horas - {ag_id}")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        info_group = QGroupBox("Información Actual")
        info_layout = QFormLayout()

        self.ag_label = QLabel(ag_id)
        self.ag_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        info_layout.addRow("AG:", self.ag_label)

        self.horas_actual_label = QLabel(f"{horas_actual:,} horas")
        self.horas_actual_label.setStyleSheet("font-size: 14px;")
        info_layout.addRow("Horas actual:", self.horas_actual_label)

        if manto_piso_hecho:
            self.cont_piso_label = QLabel("✅ MANTENIMIENTO PISO HECHO")
            self.cont_piso_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        else:
            if cont_piso >= 250:
                piso_color = "#f38ba8"
                piso_text = f"🔴 REQUIERE MANTENIMIENTO"
            elif cont_piso >= 225:
                piso_color = "#f9e2af"
                piso_text = f"🟡 PRÓXIMO PISO ({cont_piso}/250)"
            elif cont_piso >= 200:
                piso_color = "#a6e3a1"
                piso_text = f"🟢 PRÓXIMO PISO ({cont_piso}/250)"
            else:
                piso_color = "#a6e3a1"
                piso_text = f"{cont_piso}/250 horas"

            self.cont_piso_label = QLabel(piso_text)
            self.cont_piso_label.setStyleSheet(f"color: {piso_color}; font-weight: bold;")

        info_layout.addRow("Piso:", self.cont_piso_label)

        if cont_agencia >= 500:
            agencia_color = "#f38ba8"
            agencia_text = f"🔴 REQUIERE MANTENIMIENTO"
        elif cont_agencia >= 450:
            agencia_color = "#fab387"
            agencia_text = f"🟠 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        elif cont_agencia >= 400:
            agencia_color = "#f9e2af"
            agencia_text = f"🟡 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        elif cont_agencia >= 350:
            agencia_color = "#a6e3a1"
            agencia_text = f"🟢 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        else:
            agencia_color = "#a6e3a1"
            agencia_text = f"{cont_agencia}/500 horas"

        self.cont_agencia_label = QLabel(agencia_text)
        self.cont_agencia_label.setStyleSheet(f"color: {agencia_color}; font-weight: bold;")
        info_layout.addRow("Agencia:", self.cont_agencia_label)

        info_group.setLayout(info_layout)
        layout.addRow(info_group)

        registro_group = QGroupBox("Nuevo Registro")
        registro_layout = QFormLayout()

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        self.fecha.setEnabled(False)
        registro_layout.addRow("Fecha (hoy):", self.fecha)

        self.horas_nuevas = QLineEdit()
        self.horas_nuevas.setPlaceholderText("Ej: 8, 15, 25...")
        self.horas_nuevas.textChanged.connect(self.actualizar_preview)
        registro_layout.addRow("Horas a registrar:", self.horas_nuevas)

        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)

        self.preview_label = QLabel("Nuevo total: --- horas")
        self.preview_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        preview_layout.addWidget(self.preview_label)

        self.preview_piso = QLabel("Nuevo progreso Piso: ---")
        self.preview_agencia = QLabel("Nuevo progreso Agencia: ---")
        preview_layout.addWidget(self.preview_piso)
        preview_layout.addWidget(self.preview_agencia)

        registro_layout.addRow("", self.preview_frame)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(80)
        self.observaciones.setPlaceholderText("Observaciones (opcional)")
        registro_layout.addRow("Observaciones:", self.observaciones)

        registro_group.setLayout(registro_layout)
        layout.addRow(registro_group)

        self.horas_actual_valor = horas_actual
        self.cont_piso_valor = cont_piso
        self.cont_agencia_valor = cont_agencia
        self.manto_piso_hecho = manto_piso_hecho

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def actualizar_preview(self):
        try:
            horas_nuevas = int(self.horas_nuevas.text() or 0)
            nuevo_total = self.horas_actual_valor + horas_nuevas
            self.preview_label.setText(f"Nuevo total: {nuevo_total:,} horas")

            if self.manto_piso_hecho:
                self.preview_piso.setText("Nuevo progreso Piso: ✅ MANTENIMIENTO HECHO (congelado)")
                self.preview_piso.setStyleSheet("color: #89b4fa;")
            else:
                nuevo_piso = self.cont_piso_valor + horas_nuevas
                if nuevo_piso >= 250:
                    piso_color = "#f38ba8"
                    piso_text = f"🔴 REQUIERE MANTENIMIENTO ({nuevo_piso}/250)"
                elif nuevo_piso >= 225:
                    piso_color = "#f9e2af"
                    piso_text = f"🟡 PRÓXIMO PISO ({nuevo_piso}/250)"
                elif nuevo_piso >= 200:
                    piso_color = "#a6e3a1"
                    piso_text = f"🟢 PRÓXIMO PISO ({nuevo_piso}/250)"
                else:
                    piso_color = "#a6e3a1"
                    piso_text = f"{nuevo_piso}/250 horas"

                self.preview_piso.setText(f"Nuevo progreso Piso: {piso_text}")
                self.preview_piso.setStyleSheet(f"color: {piso_color};")

            nuevo_agencia = self.cont_agencia_valor + horas_nuevas
            if nuevo_agencia >= 500:
                agencia_color = "#f38ba8"
                agencia_text = f"🔴 REQUIERE MANTENIMIENTO ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 450:
                agencia_color = "#fab387"
                agencia_text = f"🟠 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 400:
                agencia_color = "#f9e2af"
                agencia_text = f"🟡 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 350:
                agencia_color = "#a6e3a1"
                agencia_text = f"🟢 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            else:
                agencia_color = "#a6e3a1"
                agencia_text = f"{nuevo_agencia}/500 horas"

            self.preview_agencia.setText(f"Nuevo progreso Agencia: {agencia_text}")
            self.preview_agencia.setStyleSheet(f"color: {agencia_color};")

        except:
            self.preview_label.setText("Nuevo total: --- horas")
            self.preview_piso.setText("Nuevo progreso Piso: ---")
            self.preview_agencia.setText("Nuevo progreso Agencia: ---")

    def get_data(self):
        try:
            return {
                'horas_nuevas': int(self.horas_nuevas.text()),
                'fecha': self.fecha.date().toPyDate(),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
            return None

class DialogoMantenimientoPisoAG(QDialog):
    def __init__(self, ag_id, contador_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mantenimiento Piso - {ag_id}")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        info_label = QLabel(f"AG: {ag_id}")
        info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        layout.addRow(info_label)

        layout.addRow(QLabel("✅ Mantenimiento de PISO completado"))
        layout.addRow(QLabel(f"Contador actual: {contador_actual}/250 horas"))
        layout.addRow(QLabel("Se marcará como HECHO y se congelará el contador"))
        layout.addRow(QLabel("hasta el próximo mantenimiento de AGENCIA."))

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        layout.addRow("Fecha:", self.fecha)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones del mantenimiento...")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'fecha': self.fecha.date().toPyDate(),
            'observaciones': self.observaciones.toPlainText()
        }

class DialogoMantenimientoAgenciaAG(QDialog):
    def __init__(self, ag_id, contador_piso, contador_agencia, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mantenimiento Agencia - {ag_id}")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        info_label = QLabel(f"AG: {ag_id}")
        info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        layout.addRow(info_label)

        layout.addRow(QLabel("🏢 Mantenimiento de AGENCIA completado"))
        layout.addRow(QLabel(f"Contador Piso: {contador_piso}/250 horas"))
        layout.addRow(QLabel(f"Contador Agencia: {contador_agencia}/500 horas"))
        layout.addRow(QLabel("⚠️ Se reiniciarán AMBOS contadores a 0"))

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        layout.addRow("Fecha:", self.fecha)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones del mantenimiento...")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'fecha': self.fecha.date().toPyDate(),
            'observaciones': self.observaciones.toPlainText()
        }

class DialogoEditarHorasAG(QDialog):
    def __init__(self, ag_id, horas_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Horas - {ag_id}")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        layout.addRow(QLabel(f"AG: {ag_id}"))
        layout.addRow(QLabel(f"Horas actual: {horas_actual:,} horas"))

        self.nuevas_horas = QLineEdit()
        self.nuevas_horas.setPlaceholderText("Ingrese las horas correctas")
        self.nuevas_horas.setText(str(horas_actual))
        layout.addRow("Nuevas horas:", self.nuevas_horas)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(80)
        self.observaciones.setPlaceholderText("Motivo de la corrección...")
        layout.addRow("Motivo:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        try:
            return {
                'nuevas_horas': int(self.nuevas_horas.text()),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
            return None

class DialogoAgregarAG(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Nuevo AG")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.ag_id = QLineEdit()
        self.ag_id.setPlaceholderText("Ej: AG-01")
        layout.addRow("ID del AG:", self.ag_id)

        self.horas = QLineEdit()
        self.horas.setPlaceholderText("Horas iniciales")
        layout.addRow("Horas base:", self.horas)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones (opcional)")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        try:
            return {
                'ag_id': self.ag_id.text().strip().upper(),
                'horas': int(self.horas.text() or 0),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido para horas")
            return None

class DialogoHistorialAG(QDialog):
    def __init__(self, ag_id, historial, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Historial - {ag_id}")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        title = QLabel(f"📋 Historial de Registros - {ag_id}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(title)

        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["Fecha", "Horas Registradas", "Horas Total", "Tipo", "Observaciones"])
        tabla.horizontalHeader().setStretchLastSection(True)

        tabla.setRowCount(len(historial))
        for i, row in enumerate(historial):
            for j, val in enumerate(row):
                if j == 1 or j == 2:
                    item = QTableWidgetItem(f"{val:,}" if val else "0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                else:
                    item = QTableWidgetItem(str(val))
                tabla.setItem(i, j, item)

        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

# ============================================
# DIÁLOGOS THA
# ============================================
class DialogoRegistrarHorasTHA(QDialog):
    def __init__(self, tha_id, horas_actual, cont_piso, cont_agencia, manto_piso_hecho, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Registrar Horas - {tha_id}")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        info_group = QGroupBox("Información Actual")
        info_layout = QFormLayout()

        self.tha_label = QLabel(tha_id)
        self.tha_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        info_layout.addRow("THA:", self.tha_label)

        self.horas_actual_label = QLabel(f"{horas_actual:,} horas")
        self.horas_actual_label.setStyleSheet("font-size: 14px;")
        info_layout.addRow("Horas actual:", self.horas_actual_label)

        if manto_piso_hecho:
            self.cont_piso_label = QLabel("✅ MANTENIMIENTO PISO HECHO")
            self.cont_piso_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        else:
            if cont_piso >= 250:
                piso_color = "#f38ba8"
                piso_text = f"🔴 REQUIERE MANTENIMIENTO"
            elif cont_piso >= 225:
                piso_color = "#f9e2af"
                piso_text = f"🟡 PRÓXIMO PISO ({cont_piso}/250)"
            elif cont_piso >= 200:
                piso_color = "#a6e3a1"
                piso_text = f"🟢 PRÓXIMO PISO ({cont_piso}/250)"
            else:
                piso_color = "#a6e3a1"
                piso_text = f"{cont_piso}/250 horas"

            self.cont_piso_label = QLabel(piso_text)
            self.cont_piso_label.setStyleSheet(f"color: {piso_color}; font-weight: bold;")

        info_layout.addRow("Piso:", self.cont_piso_label)

        if cont_agencia >= 500:
            agencia_color = "#f38ba8"
            agencia_text = f"🔴 REQUIERE MANTENIMIENTO"
        elif cont_agencia >= 450:
            agencia_color = "#fab387"
            agencia_text = f"🟠 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        elif cont_agencia >= 400:
            agencia_color = "#f9e2af"
            agencia_text = f"🟡 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        elif cont_agencia >= 350:
            agencia_color = "#a6e3a1"
            agencia_text = f"🟢 PRÓXIMO AGENCIA ({cont_agencia}/500)"
        else:
            agencia_color = "#a6e3a1"
            agencia_text = f"{cont_agencia}/500 horas"

        self.cont_agencia_label = QLabel(agencia_text)
        self.cont_agencia_label.setStyleSheet(f"color: {agencia_color}; font-weight: bold;")
        info_layout.addRow("Agencia:", self.cont_agencia_label)

        info_group.setLayout(info_layout)
        layout.addRow(info_group)

        registro_group = QGroupBox("Nuevo Registro")
        registro_layout = QFormLayout()

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        self.fecha.setEnabled(False)
        registro_layout.addRow("Fecha (hoy):", self.fecha)

        self.horas_nuevas = QLineEdit()
        self.horas_nuevas.setPlaceholderText("Ej: 8, 15, 25...")
        self.horas_nuevas.textChanged.connect(self.actualizar_preview)
        registro_layout.addRow("Horas a registrar:", self.horas_nuevas)

        self.preview_frame = QFrame()
        preview_layout = QVBoxLayout(self.preview_frame)

        self.preview_label = QLabel("Nuevo total: --- horas")
        self.preview_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        preview_layout.addWidget(self.preview_label)

        self.preview_piso = QLabel("Nuevo progreso Piso: ---")
        self.preview_agencia = QLabel("Nuevo progreso Agencia: ---")
        preview_layout.addWidget(self.preview_piso)
        preview_layout.addWidget(self.preview_agencia)

        registro_layout.addRow("", self.preview_frame)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(80)
        self.observaciones.setPlaceholderText("Observaciones (opcional)")
        registro_layout.addRow("Observaciones:", self.observaciones)

        registro_group.setLayout(registro_layout)
        layout.addRow(registro_group)

        self.horas_actual_valor = horas_actual
        self.cont_piso_valor = cont_piso
        self.cont_agencia_valor = cont_agencia
        self.manto_piso_hecho = manto_piso_hecho

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def actualizar_preview(self):
        try:
            horas_nuevas = int(self.horas_nuevas.text() or 0)
            nuevo_total = self.horas_actual_valor + horas_nuevas
            self.preview_label.setText(f"Nuevo total: {nuevo_total:,} horas")

            if self.manto_piso_hecho:
                self.preview_piso.setText("Nuevo progreso Piso: ✅ MANTENIMIENTO HECHO (congelado)")
                self.preview_piso.setStyleSheet("color: #89b4fa;")
            else:
                nuevo_piso = self.cont_piso_valor + horas_nuevas
                if nuevo_piso >= 250:
                    piso_color = "#f38ba8"
                    piso_text = f"🔴 REQUIERE MANTENIMIENTO ({nuevo_piso}/250)"
                elif nuevo_piso >= 225:
                    piso_color = "#f9e2af"
                    piso_text = f"🟡 PRÓXIMO PISO ({nuevo_piso}/250)"
                elif nuevo_piso >= 200:
                    piso_color = "#a6e3a1"
                    piso_text = f"🟢 PRÓXIMO PISO ({nuevo_piso}/250)"
                else:
                    piso_color = "#a6e3a1"
                    piso_text = f"{nuevo_piso}/250 horas"

                self.preview_piso.setText(f"Nuevo progreso Piso: {piso_text}")
                self.preview_piso.setStyleSheet(f"color: {piso_color};")

            nuevo_agencia = self.cont_agencia_valor + horas_nuevas
            if nuevo_agencia >= 500:
                agencia_color = "#f38ba8"
                agencia_text = f"🔴 REQUIERE MANTENIMIENTO ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 450:
                agencia_color = "#fab387"
                agencia_text = f"🟠 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 400:
                agencia_color = "#f9e2af"
                agencia_text = f"🟡 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            elif nuevo_agencia >= 350:
                agencia_color = "#a6e3a1"
                agencia_text = f"🟢 PRÓXIMO AGENCIA ({nuevo_agencia}/500)"
            else:
                agencia_color = "#a6e3a1"
                agencia_text = f"{nuevo_agencia}/500 horas"

            self.preview_agencia.setText(f"Nuevo progreso Agencia: {agencia_text}")
            self.preview_agencia.setStyleSheet(f"color: {agencia_color};")

        except:
            self.preview_label.setText("Nuevo total: --- horas")
            self.preview_piso.setText("Nuevo progreso Piso: ---")
            self.preview_agencia.setText("Nuevo progreso Agencia: ---")

    def get_data(self):
        try:
            return {
                'horas_nuevas': int(self.horas_nuevas.text()),
                'fecha': self.fecha.date().toPyDate(),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
            return None

class DialogoMantenimientoPisoTHA(QDialog):
    def __init__(self, tha_id, contador_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mantenimiento Piso - {tha_id}")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        info_label = QLabel(f"THA: {tha_id}")
        info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        layout.addRow(info_label)

        layout.addRow(QLabel("✅ Mantenimiento de PISO completado"))
        layout.addRow(QLabel(f"Contador actual: {contador_actual}/250 horas"))
        layout.addRow(QLabel("Se marcará como HECHO y se congelará el contador"))
        layout.addRow(QLabel("hasta el próximo mantenimiento de AGENCIA."))

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        layout.addRow("Fecha:", self.fecha)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones del mantenimiento...")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'fecha': self.fecha.date().toPyDate(),
            'observaciones': self.observaciones.toPlainText()
        }

class DialogoMantenimientoAgenciaTHA(QDialog):
    def __init__(self, tha_id, contador_piso, contador_agencia, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mantenimiento Agencia - {tha_id}")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        info_label = QLabel(f"THA: {tha_id}")
        info_label.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 14px;")
        layout.addRow(info_label)

        layout.addRow(QLabel("🏢 Mantenimiento de AGENCIA completado"))
        layout.addRow(QLabel(f"Contador Piso: {contador_piso}/250 horas"))
        layout.addRow(QLabel(f"Contador Agencia: {contador_agencia}/500 horas"))
        layout.addRow(QLabel("⚠️ Se reiniciarán AMBOS contadores a 0"))

        self.fecha = QDateEdit()
        self.fecha.setDate(QDate.currentDate())
        self.fecha.setCalendarPopup(True)
        layout.addRow("Fecha:", self.fecha)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones del mantenimiento...")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'fecha': self.fecha.date().toPyDate(),
            'observaciones': self.observaciones.toPlainText()
        }

class DialogoEditarHorasTHA(QDialog):
    def __init__(self, tha_id, horas_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Horas - {tha_id}")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        layout.addRow(QLabel(f"THA: {tha_id}"))
        layout.addRow(QLabel(f"Horas actual: {horas_actual:,} horas"))

        self.nuevas_horas = QLineEdit()
        self.nuevas_horas.setPlaceholderText("Ingrese las horas correctas")
        self.nuevas_horas.setText(str(horas_actual))
        layout.addRow("Nuevas horas:", self.nuevas_horas)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(80)
        self.observaciones.setPlaceholderText("Motivo de la corrección...")
        layout.addRow("Motivo:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        try:
            return {
                'nuevas_horas': int(self.nuevas_horas.text()),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido")
            return None

class DialogoAgregarTHA(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Nuevo THA")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.tha_id = QLineEdit()
        self.tha_id.setPlaceholderText("Ej: THA-01")
        layout.addRow("ID del THA:", self.tha_id)

        self.horas = QLineEdit()
        self.horas.setPlaceholderText("Horas iniciales")
        layout.addRow("Horas base:", self.horas)

        self.observaciones = QTextEdit()
        self.observaciones.setMaximumHeight(100)
        self.observaciones.setPlaceholderText("Observaciones (opcional)")
        layout.addRow("Observaciones:", self.observaciones)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        try:
            return {
                'tha_id': self.tha_id.text().strip().upper(),
                'horas': int(self.horas.text() or 0),
                'observaciones': self.observaciones.toPlainText()
            }
        except ValueError:
            QMessageBox.warning(self, "Error", "Ingresa un número válido para horas")
            return None

class DialogoHistorialTHA(QDialog):
    def __init__(self, tha_id, historial, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Historial - {tha_id}")
        self.setModal(True)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        title = QLabel(f"📋 Historial de Registros - {tha_id}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(title)

        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(["Fecha", "Horas Registradas", "Horas Total", "Tipo", "Observaciones"])
        tabla.horizontalHeader().setStretchLastSection(True)

        tabla.setRowCount(len(historial))
        for i, row in enumerate(historial):
            for j, val in enumerate(row):
                if j == 1 or j == 2:
                    item = QTableWidgetItem(f"{val:,}" if val else "0")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                else:
                    item = QTableWidgetItem(str(val))
                tabla.setItem(i, j, item)

        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

# ============================================
# CLASE CHECKLISTWIDGET
# ============================================
class ChecklistWidget(QWidget):
    def __init__(self, vehiculo_id, db, tipo_vehiculo='ak', parent=None):
        super().__init__(parent)
        self.vehiculo_id = vehiculo_id
        self.db = db
        self.tipo_vehiculo = tipo_vehiculo

        self.componentes = [
            "Faro izquierdo",
            "Faro derecho",
            "Foco delantero izquierdo",
            "Foco delantero derecho",
            "Foco trasero izquierdo",
            "Foco trasero derecho",
            "Llanta delantera izquierda",
            "Llanta delantera derecha",
            "Llanta trasera izquierda",
            "Llanta trasera derecha",
            "Pistón",
            "Radio",
            "Luces altas",
            "Luces bajas",
            "Direccionales",
            "Botiquín de primeros auxilios",
            "Extintor",
            "Cinturones de seguridad",
            "Espejos laterales",
            "Parabrisas",
            "Limpiaparabrisas",
            "Claxon",
            "Aire acondicionado",
            "Calefacción"
        ]

        self.checklist_items = {}
        self.observaciones_items = {}

        self.initUI()
        self.cargar_checklist()

    def initUI(self):
        layout = QVBoxLayout(self)

        title = QLabel(f"✅ Checklist de Estado - {self.vehiculo_id}")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa; padding: 5px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #313244; border: 1px solid #45475a; border-radius: 5px;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        grid = QGridLayout()
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 3)

        header_componente = QLabel("Componente")
        header_componente.setStyleSheet("font-weight: bold; color: #89b4fa;")
        header_estado = QLabel("Estado")
        header_estado.setStyleSheet("font-weight: bold; color: #89b4fa;")
        header_obs = QLabel("Observaciones")
        header_obs.setStyleSheet("font-weight: bold; color: #89b4fa;")

        grid.addWidget(header_componente, 0, 0)
        grid.addWidget(header_estado, 0, 1)
        grid.addWidget(header_obs, 0, 2)

        for i, componente in enumerate(self.componentes, start=1):
            lbl = QLabel(componente)
            lbl.setStyleSheet("padding: 3px;")
            grid.addWidget(lbl, i, 0)

            combo = QComboBox()
            combo.addItems(["✅ OK", "❌ NO CUMPLE", "⚠️ CON OBSERVACIONES"])
            combo.setStyleSheet("""
                QComboBox {
                    background-color: #45475a;
                    color: #cdd6f4;
                    border: 1px solid #585b70;
                    border-radius: 3px;
                    padding: 3px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #313244;
                    color: #cdd6f4;
                    selection-background-color: #89b4fa;
                }
            """)
            combo.currentTextChanged.connect(lambda text, c=componente: self.on_estado_changed(c, text))
            grid.addWidget(combo, i, 1)
            self.checklist_items[componente] = combo

            obs = QLineEdit()
            obs.setPlaceholderText("Observaciones...")
            obs.setStyleSheet("background-color: #45475a; color: #cdd6f4; border: 1px solid #585b70; border-radius: 3px; padding: 3px;")
            obs.textChanged.connect(lambda text, c=componente: self.on_observacion_changed(c, text))
            grid.addWidget(obs, i, 2)
            self.observaciones_items[componente] = obs

        scroll_layout.addLayout(grid)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()

        self.btn_guardar = QPushButton("💾 Guardar Checklist")
        self.btn_guardar.clicked.connect(self.guardar_checklist)
        self.btn_guardar.setStyleSheet("background-color: #a6e3a1;")

        self.btn_limpiar = QPushButton("🗑️ Limpiar Todo")
        self.btn_limpiar.clicked.connect(self.limpiar_checklist)
        self.btn_limpiar.setStyleSheet("background-color: #f38ba8;")

        btn_layout.addWidget(self.btn_guardar)
        btn_layout.addWidget(self.btn_limpiar)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def on_estado_changed(self, componente, texto):
        pass

    def on_observacion_changed(self, componente, texto):
        pass

    def cargar_checklist(self):
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT componente, estado, observaciones
                FROM checklist_vehiculos
                WHERE vehiculo_id = ? AND tipo_vehiculo = ?
            ''', (self.vehiculo_id, self.tipo_vehiculo))

            resultados = cursor.fetchall()
            for componente, estado, observaciones in resultados:
                if componente in self.checklist_items:
                    if estado == "OK":
                        self.checklist_items[componente].setCurrentText("✅ OK")
                    elif estado == "NO CUMPLE":
                        self.checklist_items[componente].setCurrentText("❌ NO CUMPLE")
                    elif estado == "CON OBSERVACIONES":
                        self.checklist_items[componente].setCurrentText("⚠️ CON OBSERVACIONES")

                if componente in self.observaciones_items and observaciones:
                    self.observaciones_items[componente].setText(observaciones)

            conn.close()
        except Exception as e:
            print(f"Error cargando checklist: {e}")

    def guardar_checklist(self):
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            for componente in self.componentes:
                if componente in self.checklist_items:
                    texto_combo = self.checklist_items[componente].currentText()
                    estado = texto_combo.replace("✅ ", "").replace("❌ ", "").replace("⚠️ ", "")

                    observaciones = self.observaciones_items[componente].text() if componente in self.observaciones_items else ""

                    cursor.execute('''
                        INSERT OR REPLACE INTO checklist_vehiculos
                        (vehiculo_id, tipo_vehiculo, componente, estado, observaciones, fecha_actualizacion)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (self.vehiculo_id, self.tipo_vehiculo, componente, estado, observaciones,
                          datetime.now().isoformat()))

            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Checklist guardado correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el checklist: {e}")

    def limpiar_checklist(self):
        reply = QMessageBox.question(self, "Confirmar",
                                    "¿Estás seguro de limpiar todo el checklist?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            for componente in self.componentes:
                if componente in self.checklist_items:
                    self.checklist_items[componente].setCurrentText("✅ OK")
                if componente in self.observaciones_items:
                    self.observaciones_items[componente].clear()

# ============================================
# CLASE VEHICULOIMAGEVIEWER (CORREGIDA)
# ============================================
class VehiculoImageViewer(QWidget):
    def __init__(self, imagen_path, vehiculo_id, db, tipo_vehiculo='ak', parent=None):
        super().__init__(parent)
        self.imagen_path = imagen_path
        self.vehiculo_id = vehiculo_id
        self.db = db
        self.tipo_vehiculo = tipo_vehiculo
        self.danos = []
        self.escala = 1.0
        self.dibujando = False
        self.punto_inicio = None
        self.tipo_dibujo = "rectangulo"
        self.pixmap_original = None

        self.initUI()
        self.cargar_danos()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()

        self.btn_rectangulo = QPushButton("⬜ Rectángulo")
        self.btn_rectangulo.setCheckable(True)
        self.btn_rectangulo.setChecked(True)
        self.btn_rectangulo.clicked.connect(lambda: self.set_tipo("rectangulo"))

        self.btn_circulo = QPushButton("⚪ Círculo")
        self.btn_circulo.setCheckable(True)
        self.btn_circulo.clicked.connect(lambda: self.set_tipo("circulo"))

        self.btn_guardar = QPushButton("💾 Guardar")
        self.btn_guardar.clicked.connect(self.guardar_danos)

        self.btn_limpiar = QPushButton("🗑️ Limpiar")
        self.btn_limpiar.clicked.connect(self.limpiar_danos)

        toolbar.addWidget(self.btn_rectangulo)
        toolbar.addWidget(self.btn_circulo)
        toolbar.addWidget(self.btn_guardar)
        toolbar.addWidget(self.btn_limpiar)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("background-color: #2a2a3a; border: 1px solid #45475a;")

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background-color: transparent;")
        self.label.setMinimumHeight(300)

        # Verificar si la imagen existe
        if os.path.exists(self.imagen_path):
            self.pixmap_original = QPixmap(self.imagen_path)
            if not self.pixmap_original.isNull():
                self.actualizar_imagen()
            else:
                self.label.setText(f"❌ Error al cargar la imagen: {self.imagen_path}\nEl formato podría no ser compatible.")
                self.label.setStyleSheet("color: red; padding: 20px; font-size: 14px;")
        else:
            self.label.setText(f"❌ Imagen no encontrada: {self.imagen_path}\nVerifica que la ruta sea correcta.")
            self.label.setStyleSheet("color: red; padding: 20px; font-size: 14px;")

        self.scroll.setWidget(self.label)
        layout.addWidget(self.scroll)

        info = QLabel(f"Vehículo: {self.vehiculo_id} | Daños: 0")
        info.setStyleSheet("padding: 5px; background-color: #313244; border-radius: 5px;")
        layout.addWidget(info)
        self.info_label = info

        self.label.mousePressEvent = self.mouse_press_event
        self.label.mouseMoveEvent = self.mouse_move_event
        self.label.mouseReleaseEvent = self.mouse_release_event

    def set_tipo(self, tipo):
        self.tipo_dibujo = tipo
        self.btn_rectangulo.setChecked(tipo == "rectangulo")
        self.btn_circulo.setChecked(tipo == "circulo")

    def actualizar_imagen(self):
        if self.pixmap_original and not self.pixmap_original.isNull():
            pixmap = self.pixmap_original
            if pixmap.width() > 700:
                pixmap = pixmap.scaledToWidth(700, Qt.TransformationMode.SmoothTransformation)

            pixmap_con_danos = QPixmap(pixmap)

            if self.danos:
                painter = QPainter(pixmap_con_danos)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                for d in self.danos:
                    color = QColor(255, 0, 0, 100)
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(Qt.GlobalColor.red, 2))

                    if d['tipo'] == 'rectangulo':
                        painter.drawRect(int(d['x']), int(d['y']), int(d['w']), int(d['h']))
                    else:
                        painter.drawEllipse(int(d['x']), int(d['y']), int(d['w']), int(d['h']))

                painter.end()

            self.label.setPixmap(pixmap_con_danos)
            self.label.setFixedSize(pixmap_con_danos.size())

    def mouse_press_event(self, event):
        if not self.pixmap_original or self.pixmap_original.isNull():
            return
        if event.button() == Qt.MouseButton.LeftButton and self.label.pixmap():
            self.dibujando = True
            self.punto_inicio = event.pos()

    def mouse_move_event(self, event):
        if not self.pixmap_original or self.pixmap_original.isNull():
            return
        if self.dibujando and self.punto_inicio and self.label.pixmap():
            pixmap_actual = self.label.pixmap()
            if pixmap_actual:
                pixmap_preview = QPixmap(pixmap_actual)
                painter = QPainter(pixmap_preview)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                x = min(self.punto_inicio.x(), event.pos().x())
                y = min(self.punto_inicio.y(), event.pos().y())
                w = abs(event.pos().x() - self.punto_inicio.x())
                h = abs(event.pos().y() - self.punto_inicio.y())

                if w > 0 and h > 0:
                    color = QColor(255, 0, 0, 100)
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(Qt.GlobalColor.red, 2))

                    if self.tipo_dibujo == 'rectangulo':
                        painter.drawRect(x, y, w, h)
                    else:
                        painter.drawEllipse(x, y, w, h)

                painter.end()
                self.label.setPixmap(pixmap_preview)

    def mouse_release_event(self, event):
        if not self.pixmap_original or self.pixmap_original.isNull():
            return
        if self.dibujando and event.button() == Qt.MouseButton.LeftButton:
            x = min(self.punto_inicio.x(), event.pos().x())
            y = min(self.punto_inicio.y(), event.pos().y())
            w = abs(event.pos().x() - self.punto_inicio.x())
            h = abs(event.pos().y() - self.punto_inicio.y())

            if w > 10 and h > 10:
                dano = {
                    'tipo': self.tipo_dibujo,
                    'x': x, 'y': y, 'w': w, 'h': h
                }
                self.danos.append(dano)
                self.actualizar_imagen()
                self.info_label.setText(f"Vehículo: {self.vehiculo_id} | Daños: {len(self.danos)}")

            self.dibujando = False

    def limpiar_danos(self):
        if not self.pixmap_original or self.pixmap_original.isNull():
            return
        reply = QMessageBox.question(self, "Confirmar", "¿Eliminar todos los daños?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.danos = []
            self.actualizar_imagen()
            self.info_label.setText(f"Vehículo: {self.vehiculo_id} | Daños: 0")

    def cargar_danos(self):
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT datos_danos FROM danos_vehiculos WHERE vehiculo_id = ? AND tipo_vehiculo = ?",
                (self.vehiculo_id, self.tipo_vehiculo)
            )
            res = cursor.fetchone()
            if res:
                self.danos = json.loads(res[0])
            conn.close()
        except Exception as e:
            print(f"Error cargando daños: {e}")

        self.actualizar_imagen()
        self.info_label.setText(f"Vehículo: {self.vehiculo_id} | Daños: {len(self.danos)}")

    def guardar_danos(self):
        if not self.pixmap_original or self.pixmap_original.isNull():
            QMessageBox.warning(self, "Advertencia", "No hay imagen base para guardar daños")
            return
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO danos_vehiculos
                (vehiculo_id, tipo_vehiculo, datos_danos, fecha_actualizacion)
                VALUES (?, ?, ?, ?)
            ''', (self.vehiculo_id, self.tipo_vehiculo, json.dumps(self.danos),
                  datetime.now().isoformat()))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Éxito", "Daños guardados correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron guardar los daños: {e}")

# ============================================
# CLASE DIALOGOVERVEHICULO
# ============================================
class DialogoVerVehiculo(QDialog):
    def __init__(self, vehiculo_data, imagen_path, db, tipo='ak', tab_inicial=0, parent=None):
        super().__init__(parent)
        self.vehiculo_data = vehiculo_data
        self.imagen_path = imagen_path
        self.db = db
        self.tipo = tipo
        self.tab_inicial = tab_inicial

        self.setWindowTitle(f"{tipo.upper()} {vehiculo_data[1]} - Inspección Completa")
        self.setModal(True)
        self.setMinimumSize(1200, 700)

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        info_panel = QFrame()
        info_panel.setStyleSheet("background-color: #313244; border-radius: 5px; padding: 5px;")
        info_layout = QHBoxLayout(info_panel)

        title = QLabel(f"🚛 {self.tipo.upper()}: {self.vehiculo_data[1]}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")

        if self.tipo == 'ak':
            info = QLabel(f"Km Actual: {self.vehiculo_data[3]:,} | Piso: {self.vehiculo_data[5]}/250 | Agencia: {self.vehiculo_data[6]}/500")
        else:
            info = QLabel(f"Horas Actual: {self.vehiculo_data[3]:,} | Piso: {self.vehiculo_data[5]}/250 | Agencia: {self.vehiculo_data[6]}/500")

        info.setStyleSheet("color: #cdd6f4;")

        info_layout.addWidget(title)
        info_layout.addWidget(info)
        info_layout.addStretch()

        layout.addWidget(info_panel)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)

        self.tab_danos = QWidget()
        danos_layout = QVBoxLayout(self.tab_danos)
        self.image_viewer = VehiculoImageViewer(self.imagen_path, self.vehiculo_data[1], self.db, self.tipo, self)
        danos_layout.addWidget(self.image_viewer)

        self.tab_checklist = QWidget()
        checklist_layout = QVBoxLayout(self.tab_checklist)
        self.checklist_widget = ChecklistWidget(self.vehiculo_data[1], self.db, self.tipo, self)
        checklist_layout.addWidget(self.checklist_widget)

        self.tabs.addTab(self.tab_danos, "🖍️ Dibujar Daños")
        self.tabs.addTab(self.tab_checklist, "✅ Checklist de Estado")

        self.tabs.setCurrentIndex(self.tab_inicial)

        layout.addWidget(self.tabs)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        btn_cerrar.setMaximumWidth(100)
        layout.addWidget(btn_cerrar, alignment=Qt.AlignmentFlag.AlignRight)

# ============================================
# TABLA AK (CON RUTAS CORREGIDAS)
# ============================================
class TablaAK(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.gestion = GestionAK()
        self.imagen_ak = RUTA_IMAGEN_AK  # Usar la ruta global
        self.tipo = 'ak'
        self.initUI()
        self.cargar_datos()

    def initUI(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        self.btn_agregar = QPushButton("➕ Nuevo AK")
        self.btn_agregar.clicked.connect(self.agregar)
        toolbar.addWidget(self.btn_agregar)

        self.btn_registrar = QPushButton("📝 Registrar Km")
        self.btn_registrar.clicked.connect(self.registrar)
        toolbar.addWidget(self.btn_registrar)

        self.btn_editar = QPushButton("✏️ Editar Km")
        self.btn_editar.clicked.connect(self.editar)
        toolbar.addWidget(self.btn_editar)

        self.btn_historial = QPushButton("📋 Historial")
        self.btn_historial.clicked.connect(self.ver_historial)
        toolbar.addWidget(self.btn_historial)

        self.btn_ver_detalles = QPushButton("👁️ Ver Daños")
        self.btn_ver_detalles.clicked.connect(self.ver_detalles)
        self.btn_ver_detalles.setStyleSheet("background-color: #89b4fa;")
        toolbar.addWidget(self.btn_ver_detalles)

        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.clicked.connect(self.eliminar)
        toolbar.addWidget(self.btn_eliminar)

        toolbar.addStretch()

        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("🔍 Buscar AK...")
        self.busqueda.setMaximumWidth(200)
        self.busqueda.textChanged.connect(self.buscar)
        toolbar.addWidget(self.busqueda)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setMaximumWidth(40)
        self.btn_refresh.clicked.connect(self.cargar_datos)
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "AK", "Km Actual", "Piso (250km)", "Agencia (500km)",
            "Último Piso", "Última Agencia", "Estado", "Checklist"
        ])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSortingEnabled(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.doubleClicked.connect(self.ver_detalles)
        layout.addWidget(self.tabla)

    def obtener_resumen_checklist(self, vehiculo_id):
        try:
            conn = sqlite3.connect(self.gestion.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT estado, COUNT(*)
                FROM checklist_vehiculos
                WHERE vehiculo_id = ? AND tipo_vehiculo = ?
                GROUP BY estado
            ''', (vehiculo_id, self.tipo))

            resultados = cursor.fetchall()
            total = sum([r[1] for r in resultados])

            if total == 0:
                conn.close()
                return "📋 Pendiente", QColor(249, 226, 175), "Checklist no realizado"

            ok_count = 0
            no_cumple_count = 0
            observaciones_count = 0

            for estado, count in resultados:
                if estado == "OK":
                    ok_count = count
                elif estado == "NO CUMPLE":
                    no_cumple_count = count
                elif estado == "CON OBSERVACIONES":
                    observaciones_count = count

            conn.close()

            if no_cumple_count > 0:
                return f"⚠️ {no_cumple_count} no cumplen", QColor(243, 139, 168), f"{no_cumple_count} componentes NO CUMPLEN"
            elif observaciones_count > 0:
                return f"📝 {observaciones_count} con obs", QColor(250, 179, 135), f"{observaciones_count} componentes con observaciones"
            else:
                return f"✅ {ok_count}/{total} OK", QColor(166, 227, 161), f"{ok_count} de {total} componentes OK"

        except Exception as e:
            print(f"Error obteniendo resumen: {e}")
            return "📋 Error", QColor(243, 139, 168), "Error al cargar checklist"

    def cargar_datos(self):
        datos = self.gestion.obtener_todos()
        self.tabla.setRowCount(len(datos))

        for i, row in enumerate(datos):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(row[1])))

            km_actual = row[3]
            item_km = QTableWidgetItem(f"{km_actual:,}")
            item_km.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.tabla.setItem(i, 1, item_km)

            cont_piso = row[5]
            manto_piso_hecho = row[9] if len(row) > 9 else 0

            if manto_piso_hecho:
                item_piso = QTableWidgetItem("✅ HECHO")
                item_piso.setForeground(QBrush(QColor(137, 180, 250)))
            else:
                if cont_piso >= 250:
                    item_piso = QTableWidgetItem(f"🔴 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(243, 139, 168)))
                elif cont_piso >= 225:
                    item_piso = QTableWidgetItem(f"🟡 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(249, 226, 175)))
                elif cont_piso >= 200:
                    item_piso = QTableWidgetItem(f"🟢 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(166, 227, 161)))
                else:
                    item_piso = QTableWidgetItem(f"{cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(166, 227, 161)))

            item_piso.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 2, item_piso)

            cont_agencia = row[6]

            if cont_agencia >= 500:
                item_agencia = QTableWidgetItem(f"🔴 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(243, 139, 168)))
            elif cont_agencia >= 450:
                item_agencia = QTableWidgetItem(f"🟠 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(250, 179, 135)))
            elif cont_agencia >= 400:
                item_agencia = QTableWidgetItem(f"🟡 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(249, 226, 175)))
            elif cont_agencia >= 350:
                item_agencia = QTableWidgetItem(f"🟢 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(166, 227, 161)))
            else:
                item_agencia = QTableWidgetItem(f"{cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(166, 227, 161)))

            item_agencia.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 3, item_agencia)

            ult_piso = row[7] if len(row) > 7 and row[7] else "---"
            self.tabla.setItem(i, 4, QTableWidgetItem(str(ult_piso)))

            ult_agencia = row[8] if len(row) > 8 and row[8] else "---"
            self.tabla.setItem(i, 5, QTableWidgetItem(str(ult_agencia)))

            estado, color = self.obtener_estado(cont_piso, cont_agencia, manto_piso_hecho)
            item_estado = QTableWidgetItem(estado)
            item_estado.setForeground(QBrush(color))
            self.tabla.setItem(i, 6, item_estado)

            texto_checklist, color_checklist, tooltip = self.obtener_resumen_checklist(str(row[1]))
            item_checklist = QTableWidgetItem(texto_checklist)
            item_checklist.setForeground(QBrush(color_checklist))
            item_checklist.setToolTip(tooltip)
            item_checklist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 7, item_checklist)

        self.tabla.resizeColumnsToContents()

    def obtener_estado(self, cont_piso, cont_agencia, piso_hecho):
        if cont_agencia >= 500:
            return "🔴 REQUIERE AGENCIA", QColor(243, 139, 168)
        elif not piso_hecho and cont_piso >= 250:
            return "🔴 REQUIERE PISO", QColor(243, 139, 168)
        elif cont_agencia >= 450:
            return "🟠 PRÓXIMO AGENCIA", QColor(250, 179, 135)
        elif cont_agencia >= 400:
            return "🟡 PRÓXIMO AGENCIA", QColor(249, 226, 175)
        elif not piso_hecho and cont_piso >= 225:
            return "🟡 PRÓXIMO PISO", QColor(249, 226, 175)
        elif not piso_hecho and cont_piso >= 200:
            return "🟢 PRÓXIMO PISO", QColor(166, 227, 161)
        elif piso_hecho:
            return "✅ PISO HECHO", QColor(137, 180, 250)
        else:
            return "🟢 OK", QColor(166, 227, 161)

    def buscar(self):
        termino = self.busqueda.text()
        if len(termino) < 2:
            self.cargar_datos()
            return

        datos = self.gestion.buscar(termino)
        self.tabla.setRowCount(len(datos))

        for i, row in enumerate(datos):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(row[1])))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"{row[3]:,}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{row[5]}/250"))
            self.tabla.setItem(i, 3, QTableWidgetItem(f"{row[6]}/500"))
            self.tabla.setItem(i, 4, QTableWidgetItem(str(row[7] if row[7] else "---")))
            self.tabla.setItem(i, 5, QTableWidgetItem(str(row[8] if row[8] else "---")))

            texto_checklist, color_checklist, tooltip = self.obtener_resumen_checklist(str(row[1]))
            item_checklist = QTableWidgetItem(texto_checklist)
            item_checklist.setForeground(QBrush(color_checklist))
            item_checklist.setToolTip(tooltip)
            item_checklist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 6, item_checklist)

    def ver_detalles(self, tab_inicial=0):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un vehículo")
            return

        ak_id = self.tabla.item(row, 0).text()

        conn = sqlite3.connect(self.gestion.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ak_vehiculos WHERE ak_id = ?", (ak_id,))
        data = cursor.fetchone()
        conn.close()

        if data:
            dialog = DialogoVerVehiculo(data, self.imagen_ak, self.parent.db, self.tipo, tab_inicial, self)
            dialog.exec()
            self.cargar_datos()

    def registrar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AK")
            return

        ak_id = self.tabla.item(row, 0).text()

        texto_km = self.tabla.item(row, 1).text().replace(',', '')
        km_actual = int(texto_km)

        texto_piso = self.tabla.item(row, 2).text()
        if texto_piso == "✅ HECHO":
            cont_piso = 0
            manto_piso_hecho = True
        else:
            numeros = re.findall(r'\d+', texto_piso)
            cont_piso = int(numeros[0]) if numeros else 0
            manto_piso_hecho = False

        texto_agencia = self.tabla.item(row, 3).text()
        numeros_agencia = re.findall(r'\d+', texto_agencia)
        cont_agencia = int(numeros_agencia[0]) if numeros_agencia else 0

        dialog = DialogoRegistrarKilometrajeAK(ak_id, km_actual, cont_piso, cont_agencia, manto_piso_hecho, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                exito, manto_piso, manto_agencia, error = self.gestion.registrar_kilometraje(
                    ak_id, data['km_nuevos'], data['fecha'], data['observaciones']
                )

                if exito:
                    self.cargar_datos()

                    if manto_agencia:
                        reply = QMessageBox.question(
                            self, "Mantenimiento Agencia",
                            f"🏢 {ak_id} ha alcanzado 500 km.\n\n¿Registrar mantenimiento de AGENCIA?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._registrar_mantenimiento_agencia(ak_id)

                    elif manto_piso and not manto_piso_hecho:
                        reply = QMessageBox.question(
                            self, "Mantenimiento Piso",
                            f"✅ {ak_id} ha alcanzado 250 km.\n\n¿Registrar mantenimiento de PISO?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._registrar_mantenimiento_piso(ak_id)

                    else:
                        QMessageBox.information(self, "Éxito", f"Registrados {data['km_nuevos']} km para {ak_id}")

    def _registrar_mantenimiento_piso(self, ak_id):
        for row in range(self.tabla.rowCount()):
            if self.tabla.item(row, 0) and self.tabla.item(row, 0).text() == ak_id:
                texto_piso = self.tabla.item(row, 2).text()
                if not texto_piso.startswith("✅"):
                    numeros = re.findall(r'\d+', texto_piso)
                    cont_piso = int(numeros[0]) if numeros else 0

                    dialog = DialogoMantenimientoPisoAK(ak_id, cont_piso, self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_data()
                        if self.gestion.registrar_mantenimiento_piso(ak_id, data['fecha'], data['observaciones']):
                            self.cargar_datos()
                            QMessageBox.information(
                                self, "Éxito",
                                f"✅ Mantenimiento de PISO registrado para {ak_id} el {data['fecha']}"
                            )
                break

    def _registrar_mantenimiento_agencia(self, ak_id):
        for row in range(self.tabla.rowCount()):
            if self.tabla.item(row, 0) and self.tabla.item(row, 0).text() == ak_id:
                texto_piso = self.tabla.item(row, 2).text()
                if texto_piso.startswith("✅"):
                    cont_piso = 0
                else:
                    numeros = re.findall(r'\d+', texto_piso)
                    cont_piso = int(numeros[0]) if numeros else 0

                texto_agencia = self.tabla.item(row, 3).text()
                numeros_agencia = re.findall(r'\d+', texto_agencia)
                cont_agencia = int(numeros_agencia[0]) if numeros_agencia else 0

                dialog = DialogoMantenimientoAgenciaAK(ak_id, cont_piso, cont_agencia, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    data = dialog.get_data()
                    if self.gestion.registrar_mantenimiento_agencia(ak_id, data['fecha'], data['observaciones']):
                        self.cargar_datos()
                        QMessageBox.information(
                            self, "Éxito",
                            f"🏢 Mantenimiento de AGENCIA registrado para {ak_id} el {data['fecha']}"
                        )
                break

    def editar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AK")
            return

        ak_id = self.tabla.item(row, 0).text()
        texto_km = self.tabla.item(row, 1).text().replace(',', '')
        km_actual = int(texto_km)

        dialog = DialogoEditarKilometrajeAK(ak_id, km_actual, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                exito, mensaje = self.gestion.editar_kilometraje(ak_id, data['nuevo_km'], data['observaciones'])
                if exito:
                    self.cargar_datos()
                    QMessageBox.information(self, "Éxito", mensaje)

    def ver_historial(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AK")
            return

        ak_id = self.tabla.item(row, 0).text()
        historial = self.gestion.obtener_historial(ak_id)

        if not historial:
            QMessageBox.information(self, "Info", "No hay historial para este AK")
            return

        dialog = DialogoHistorialAK(ak_id, historial, self)
        dialog.exec()

    def agregar(self):
        dialog = DialogoAgregarAK(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                if not data['ak_id'].startswith('AK-'):
                    QMessageBox.warning(self, "Error", "El ID debe comenzar con AK-")
                    return

                if self.gestion.agregar(data['ak_id'], data['kilometraje'], data['observaciones']):
                    self.cargar_datos()
                    QMessageBox.information(self, "Éxito", f"AK {data['ak_id']} agregado")
                else:
                    QMessageBox.warning(self, "Error", f"El AK {data['ak_id']} ya existe")

    def eliminar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AK")
            return

        ak_id = self.tabla.item(row, 0).text()

        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar {ak_id}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.gestion.eliminar(ak_id):
                self.cargar_datos()
                QMessageBox.information(self, "Éxito", f"AK {ak_id} eliminado")

# ============================================
# TABLA AG (CON RUTAS CORREGIDAS)
# ============================================
class TablaAG(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.gestion = GestionAG()
        self.imagen_ag = RUTA_IMAGEN_AG  # Usar la ruta global
        self.tipo = 'ag'
        self.initUI()
        self.cargar_datos()

    def initUI(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        self.btn_agregar = QPushButton("➕ Nuevo AG")
        self.btn_agregar.clicked.connect(self.agregar)
        toolbar.addWidget(self.btn_agregar)

        self.btn_registrar = QPushButton("📝 Registrar Horas")
        self.btn_registrar.clicked.connect(self.registrar)
        toolbar.addWidget(self.btn_registrar)

        self.btn_editar = QPushButton("✏️ Editar Horas")
        self.btn_editar.clicked.connect(self.editar)
        toolbar.addWidget(self.btn_editar)

        self.btn_historial = QPushButton("📋 Historial")
        self.btn_historial.clicked.connect(self.ver_historial)
        toolbar.addWidget(self.btn_historial)

        self.btn_ver_detalles = QPushButton("👁️ Ver Daños")
        self.btn_ver_detalles.clicked.connect(self.ver_detalles)
        self.btn_ver_detalles.setStyleSheet("background-color: #89b4fa;")
        toolbar.addWidget(self.btn_ver_detalles)

        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.clicked.connect(self.eliminar)
        toolbar.addWidget(self.btn_eliminar)

        toolbar.addStretch()

        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("🔍 Buscar AG...")
        self.busqueda.setMaximumWidth(200)
        self.busqueda.textChanged.connect(self.buscar)
        toolbar.addWidget(self.busqueda)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setMaximumWidth(40)
        self.btn_refresh.clicked.connect(self.cargar_datos)
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "AG", "Horas Actual", "Piso (250h)", "Agencia (500h)",
            "Último Piso", "Última Agencia", "Estado", "Checklist"
        ])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSortingEnabled(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.doubleClicked.connect(self.ver_detalles)
        layout.addWidget(self.tabla)

    def obtener_resumen_checklist(self, vehiculo_id):
        try:
            conn = sqlite3.connect(self.gestion.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT estado, COUNT(*)
                FROM checklist_vehiculos
                WHERE vehiculo_id = ? AND tipo_vehiculo = ?
                GROUP BY estado
            ''', (vehiculo_id, self.tipo))

            resultados = cursor.fetchall()
            total = sum([r[1] for r in resultados])

            if total == 0:
                conn.close()
                return "📋 Pendiente", QColor(249, 226, 175), "Checklist no realizado"

            ok_count = 0
            no_cumple_count = 0
            observaciones_count = 0

            for estado, count in resultados:
                if estado == "OK":
                    ok_count = count
                elif estado == "NO CUMPLE":
                    no_cumple_count = count
                elif estado == "CON OBSERVACIONES":
                    observaciones_count = count

            conn.close()

            if no_cumple_count > 0:
                return f"⚠️ {no_cumple_count} no cumplen", QColor(243, 139, 168), f"{no_cumple_count} componentes NO CUMPLEN"
            elif observaciones_count > 0:
                return f"📝 {observaciones_count} con obs", QColor(250, 179, 135), f"{observaciones_count} componentes con observaciones"
            else:
                return f"✅ {ok_count}/{total} OK", QColor(166, 227, 161), f"{ok_count} de {total} componentes OK"

        except Exception as e:
            print(f"Error obteniendo resumen: {e}")
            return "📋 Error", QColor(243, 139, 168), "Error al cargar checklist"

    def cargar_datos(self):
        datos = self.gestion.obtener_todos()
        self.tabla.setRowCount(len(datos))

        for i, row in enumerate(datos):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(row[1])))

            horas_actual = row[3]
            item_horas = QTableWidgetItem(f"{horas_actual:,}")
            item_horas.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.tabla.setItem(i, 1, item_horas)

            cont_piso = row[5]
            manto_piso_hecho = row[9] if len(row) > 9 else 0

            if manto_piso_hecho:
                item_piso = QTableWidgetItem("✅ HECHO")
                item_piso.setForeground(QBrush(QColor(137, 180, 250)))
            else:
                if cont_piso >= 250:
                    item_piso = QTableWidgetItem(f"🔴 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(243, 139, 168)))
                elif cont_piso >= 225:
                    item_piso = QTableWidgetItem(f"🟡 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(249, 226, 175)))
                elif cont_piso >= 200:
                    item_piso = QTableWidgetItem(f"🟢 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(166, 227, 161)))
                else:
                    item_piso = QTableWidgetItem(f"{cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(166, 227, 161)))

            item_piso.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 2, item_piso)

            cont_agencia = row[6]

            if cont_agencia >= 500:
                item_agencia = QTableWidgetItem(f"🔴 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(243, 139, 168)))
            elif cont_agencia >= 450:
                item_agencia = QTableWidgetItem(f"🟠 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(250, 179, 135)))
            elif cont_agencia >= 400:
                item_agencia = QTableWidgetItem(f"🟡 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(249, 226, 175)))
            elif cont_agencia >= 350:
                item_agencia = QTableWidgetItem(f"🟢 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(166, 227, 161)))
            else:
                item_agencia = QTableWidgetItem(f"{cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(166, 227, 161)))

            item_agencia.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 3, item_agencia)

            ult_piso = row[7] if len(row) > 7 and row[7] else "---"
            self.tabla.setItem(i, 4, QTableWidgetItem(str(ult_piso)))

            ult_agencia = row[8] if len(row) > 8 and row[8] else "---"
            self.tabla.setItem(i, 5, QTableWidgetItem(str(ult_agencia)))

            estado, color = self.obtener_estado(cont_piso, cont_agencia, manto_piso_hecho)
            item_estado = QTableWidgetItem(estado)
            item_estado.setForeground(QBrush(color))
            self.tabla.setItem(i, 6, item_estado)

            texto_checklist, color_checklist, tooltip = self.obtener_resumen_checklist(str(row[1]))
            item_checklist = QTableWidgetItem(texto_checklist)
            item_checklist.setForeground(QBrush(color_checklist))
            item_checklist.setToolTip(tooltip)
            item_checklist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 7, item_checklist)

        self.tabla.resizeColumnsToContents()

    def obtener_estado(self, cont_piso, cont_agencia, piso_hecho):
        if cont_agencia >= 500:
            return "🔴 REQUIERE AGENCIA", QColor(243, 139, 168)
        elif not piso_hecho and cont_piso >= 250:
            return "🔴 REQUIERE PISO", QColor(243, 139, 168)
        elif cont_agencia >= 450:
            return "🟠 PRÓXIMO AGENCIA", QColor(250, 179, 135)
        elif cont_agencia >= 400:
            return "🟡 PRÓXIMO AGENCIA", QColor(249, 226, 175)
        elif not piso_hecho and cont_piso >= 225:
            return "🟡 PRÓXIMO PISO", QColor(249, 226, 175)
        elif not piso_hecho and cont_piso >= 200:
            return "🟢 PRÓXIMO PISO", QColor(166, 227, 161)
        elif piso_hecho:
            return "✅ PISO HECHO", QColor(137, 180, 250)
        else:
            return "🟢 OK", QColor(166, 227, 161)

    def buscar(self):
        termino = self.busqueda.text()
        if len(termino) < 2:
            self.cargar_datos()
            return

        datos = self.gestion.buscar(termino)
        self.tabla.setRowCount(len(datos))

        for i, row in enumerate(datos):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(row[1])))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"{row[3]:,}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{row[5]}/250"))
            self.tabla.setItem(i, 3, QTableWidgetItem(f"{row[6]}/500"))
            self.tabla.setItem(i, 4, QTableWidgetItem(str(row[7] if row[7] else "---")))
            self.tabla.setItem(i, 5, QTableWidgetItem(str(row[8] if row[8] else "---")))

            texto_checklist, color_checklist, tooltip = self.obtener_resumen_checklist(str(row[1]))
            item_checklist = QTableWidgetItem(texto_checklist)
            item_checklist.setForeground(QBrush(color_checklist))
            item_checklist.setToolTip(tooltip)
            item_checklist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 6, item_checklist)

    def ver_detalles(self, tab_inicial=0):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un vehículo")
            return

        ag_id = self.tabla.item(row, 0).text()

        conn = sqlite3.connect(self.gestion.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ag_vehiculos WHERE ag_id = ?", (ag_id,))
        data = cursor.fetchone()
        conn.close()

        if data:
            dialog = DialogoVerVehiculo(data, self.imagen_ag, self.parent.db, self.tipo, tab_inicial, self)
            dialog.exec()
            self.cargar_datos()

    def registrar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AG")
            return

        ag_id = self.tabla.item(row, 0).text()

        texto_horas = self.tabla.item(row, 1).text().replace(',', '')
        horas_actual = int(texto_horas)

        texto_piso = self.tabla.item(row, 2).text()
        if texto_piso == "✅ HECHO":
            cont_piso = 0
            manto_piso_hecho = True
        else:
            numeros = re.findall(r'\d+', texto_piso)
            cont_piso = int(numeros[0]) if numeros else 0
            manto_piso_hecho = False

        texto_agencia = self.tabla.item(row, 3).text()
        numeros_agencia = re.findall(r'\d+', texto_agencia)
        cont_agencia = int(numeros_agencia[0]) if numeros_agencia else 0

        dialog = DialogoRegistrarHorasAG(ag_id, horas_actual, cont_piso, cont_agencia, manto_piso_hecho, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                exito, manto_piso, manto_agencia, error = self.gestion.registrar_horas(
                    ag_id, data['horas_nuevas'], data['fecha'], data['observaciones']
                )

                if exito:
                    self.cargar_datos()

                    if manto_agencia:
                        reply = QMessageBox.question(
                            self, "Mantenimiento Agencia",
                            f"🏢 {ag_id} ha alcanzado 500 horas.\n\n¿Registrar mantenimiento de AGENCIA?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._registrar_mantenimiento_agencia(ag_id)

                    elif manto_piso and not manto_piso_hecho:
                        reply = QMessageBox.question(
                            self, "Mantenimiento Piso",
                            f"✅ {ag_id} ha alcanzado 250 horas.\n\n¿Registrar mantenimiento de PISO?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._registrar_mantenimiento_piso(ag_id)

                    else:
                        QMessageBox.information(self, "Éxito", f"Registradas {data['horas_nuevas']} horas para {ag_id}")

    def _registrar_mantenimiento_piso(self, ag_id):
        for row in range(self.tabla.rowCount()):
            if self.tabla.item(row, 0) and self.tabla.item(row, 0).text() == ag_id:
                texto_piso = self.tabla.item(row, 2).text()
                if not texto_piso.startswith("✅"):
                    numeros = re.findall(r'\d+', texto_piso)
                    cont_piso = int(numeros[0]) if numeros else 0

                    dialog = DialogoMantenimientoPisoAG(ag_id, cont_piso, self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_data()
                        if self.gestion.registrar_mantenimiento_piso(ag_id, data['fecha'], data['observaciones']):
                            self.cargar_datos()
                            QMessageBox.information(
                                self, "Éxito",
                                f"✅ Mantenimiento de PISO registrado para {ag_id} el {data['fecha']}"
                            )
                break

    def _registrar_mantenimiento_agencia(self, ag_id):
        for row in range(self.tabla.rowCount()):
            if self.tabla.item(row, 0) and self.tabla.item(row, 0).text() == ag_id:
                texto_piso = self.tabla.item(row, 2).text()
                if texto_piso.startswith("✅"):
                    cont_piso = 0
                else:
                    numeros = re.findall(r'\d+', texto_piso)
                    cont_piso = int(numeros[0]) if numeros else 0

                texto_agencia = self.tabla.item(row, 3).text()
                numeros_agencia = re.findall(r'\d+', texto_agencia)
                cont_agencia = int(numeros_agencia[0]) if numeros_agencia else 0

                dialog = DialogoMantenimientoAgenciaAG(ag_id, cont_piso, cont_agencia, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    data = dialog.get_data()
                    if self.gestion.registrar_mantenimiento_agencia(ag_id, data['fecha'], data['observaciones']):
                        self.cargar_datos()
                        QMessageBox.information(
                            self, "Éxito",
                            f"🏢 Mantenimiento de AGENCIA registrado para {ag_id} el {data['fecha']}"
                        )
                break

    def editar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AG")
            return

        ag_id = self.tabla.item(row, 0).text()
        texto_horas = self.tabla.item(row, 1).text().replace(',', '')
        horas_actual = int(texto_horas)

        dialog = DialogoEditarHorasAG(ag_id, horas_actual, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                exito, mensaje = self.gestion.editar_horas(ag_id, data['nuevas_horas'], data['observaciones'])
                if exito:
                    self.cargar_datos()
                    QMessageBox.information(self, "Éxito", mensaje)

    def ver_historial(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AG")
            return

        ag_id = self.tabla.item(row, 0).text()
        historial = self.gestion.obtener_historial(ag_id)

        if not historial:
            QMessageBox.information(self, "Info", "No hay historial para este AG")
            return

        dialog = DialogoHistorialAG(ag_id, historial, self)
        dialog.exec()

    def agregar(self):
        dialog = DialogoAgregarAG(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                if not data['ag_id'].startswith('AG-'):
                    QMessageBox.warning(self, "Error", "El ID debe comenzar con AG-")
                    return

                if self.gestion.agregar(data['ag_id'], data['horas'], data['observaciones']):
                    self.cargar_datos()
                    QMessageBox.information(self, "Éxito", f"AG {data['ag_id']} agregado")
                else:
                    QMessageBox.warning(self, "Error", f"El AG {data['ag_id']} ya existe")

    def eliminar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un AG")
            return

        ag_id = self.tabla.item(row, 0).text()

        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar {ag_id}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.gestion.eliminar(ag_id):
                self.cargar_datos()
                QMessageBox.information(self, "Éxito", f"AG {ag_id} eliminado")

# ============================================
# TABLA THA (CON RUTAS CORREGIDAS)
# ============================================
class TablaTHA(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.gestion = GestionTHA()
        self.imagen_tha = RUTA_IMAGEN_THA  # Usar la ruta global
        self.tipo = 'tha'
        self.initUI()
        self.cargar_datos()

    def initUI(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()

        self.btn_agregar = QPushButton("➕ Nuevo THA")
        self.btn_agregar.clicked.connect(self.agregar)
        toolbar.addWidget(self.btn_agregar)

        self.btn_registrar = QPushButton("📝 Registrar Horas")
        self.btn_registrar.clicked.connect(self.registrar)
        toolbar.addWidget(self.btn_registrar)

        self.btn_editar = QPushButton("✏️ Editar Horas")
        self.btn_editar.clicked.connect(self.editar)
        toolbar.addWidget(self.btn_editar)

        self.btn_historial = QPushButton("📋 Historial")
        self.btn_historial.clicked.connect(self.ver_historial)
        toolbar.addWidget(self.btn_historial)

        self.btn_ver_detalles = QPushButton("👁️ Ver Daños")
        self.btn_ver_detalles.clicked.connect(self.ver_detalles)
        self.btn_ver_detalles.setStyleSheet("background-color: #89b4fa;")
        toolbar.addWidget(self.btn_ver_detalles)

        self.btn_eliminar = QPushButton("🗑️ Eliminar")
        self.btn_eliminar.clicked.connect(self.eliminar)
        toolbar.addWidget(self.btn_eliminar)

        toolbar.addStretch()

        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("🔍 Buscar THA...")
        self.busqueda.setMaximumWidth(200)
        self.busqueda.textChanged.connect(self.buscar)
        toolbar.addWidget(self.busqueda)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setMaximumWidth(40)
        self.btn_refresh.clicked.connect(self.cargar_datos)
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "THA", "Horas Actual", "Piso (250h)", "Agencia (500h)",
            "Último Piso", "Última Agencia", "Estado", "Checklist"
        ])
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSortingEnabled(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.doubleClicked.connect(self.ver_detalles)
        layout.addWidget(self.tabla)

    def obtener_resumen_checklist(self, vehiculo_id):
        try:
            conn = sqlite3.connect(self.gestion.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT estado, COUNT(*)
                FROM checklist_vehiculos
                WHERE vehiculo_id = ? AND tipo_vehiculo = ?
                GROUP BY estado
            ''', (vehiculo_id, self.tipo))

            resultados = cursor.fetchall()
            total = sum([r[1] for r in resultados])

            if total == 0:
                conn.close()
                return "📋 Pendiente", QColor(249, 226, 175), "Checklist no realizado"

            ok_count = 0
            no_cumple_count = 0
            observaciones_count = 0

            for estado, count in resultados:
                if estado == "OK":
                    ok_count = count
                elif estado == "NO CUMPLE":
                    no_cumple_count = count
                elif estado == "CON OBSERVACIONES":
                    observaciones_count = count

            conn.close()

            if no_cumple_count > 0:
                return f"⚠️ {no_cumple_count} no cumplen", QColor(243, 139, 168), f"{no_cumple_count} componentes NO CUMPLEN"
            elif observaciones_count > 0:
                return f"📝 {observaciones_count} con obs", QColor(250, 179, 135), f"{observaciones_count} componentes con observaciones"
            else:
                return f"✅ {ok_count}/{total} OK", QColor(166, 227, 161), f"{ok_count} de {total} componentes OK"

        except Exception as e:
            print(f"Error obteniendo resumen: {e}")
            return "📋 Error", QColor(243, 139, 168), "Error al cargar checklist"

    def cargar_datos(self):
        datos = self.gestion.obtener_todos()
        self.tabla.setRowCount(len(datos))

        for i, row in enumerate(datos):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(row[1])))

            horas_actual = row[3]
            item_horas = QTableWidgetItem(f"{horas_actual:,}")
            item_horas.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.tabla.setItem(i, 1, item_horas)

            cont_piso = row[5]
            manto_piso_hecho = row[9] if len(row) > 9 else 0

            if manto_piso_hecho:
                item_piso = QTableWidgetItem("✅ HECHO")
                item_piso.setForeground(QBrush(QColor(137, 180, 250)))
            else:
                if cont_piso >= 250:
                    item_piso = QTableWidgetItem(f"🔴 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(243, 139, 168)))
                elif cont_piso >= 225:
                    item_piso = QTableWidgetItem(f"🟡 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(249, 226, 175)))
                elif cont_piso >= 200:
                    item_piso = QTableWidgetItem(f"🟢 {cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(166, 227, 161)))
                else:
                    item_piso = QTableWidgetItem(f"{cont_piso}/250")
                    item_piso.setForeground(QBrush(QColor(166, 227, 161)))

            item_piso.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 2, item_piso)

            cont_agencia = row[6]

            if cont_agencia >= 500:
                item_agencia = QTableWidgetItem(f"🔴 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(243, 139, 168)))
            elif cont_agencia >= 450:
                item_agencia = QTableWidgetItem(f"🟠 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(250, 179, 135)))
            elif cont_agencia >= 400:
                item_agencia = QTableWidgetItem(f"🟡 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(249, 226, 175)))
            elif cont_agencia >= 350:
                item_agencia = QTableWidgetItem(f"🟢 {cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(166, 227, 161)))
            else:
                item_agencia = QTableWidgetItem(f"{cont_agencia}/500")
                item_agencia.setForeground(QBrush(QColor(166, 227, 161)))

            item_agencia.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 3, item_agencia)

            ult_piso = row[7] if len(row) > 7 and row[7] else "---"
            self.tabla.setItem(i, 4, QTableWidgetItem(str(ult_piso)))

            ult_agencia = row[8] if len(row) > 8 and row[8] else "---"
            self.tabla.setItem(i, 5, QTableWidgetItem(str(ult_agencia)))

            estado, color = self.obtener_estado(cont_piso, cont_agencia, manto_piso_hecho)
            item_estado = QTableWidgetItem(estado)
            item_estado.setForeground(QBrush(color))
            self.tabla.setItem(i, 6, item_estado)

            texto_checklist, color_checklist, tooltip = self.obtener_resumen_checklist(str(row[1]))
            item_checklist = QTableWidgetItem(texto_checklist)
            item_checklist.setForeground(QBrush(color_checklist))
            item_checklist.setToolTip(tooltip)
            item_checklist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 7, item_checklist)

        self.tabla.resizeColumnsToContents()

    def obtener_estado(self, cont_piso, cont_agencia, piso_hecho):
        if cont_agencia >= 500:
            return "🔴 REQUIERE AGENCIA", QColor(243, 139, 168)
        elif not piso_hecho and cont_piso >= 250:
            return "🔴 REQUIERE PISO", QColor(243, 139, 168)
        elif cont_agencia >= 450:
            return "🟠 PRÓXIMO AGENCIA", QColor(250, 179, 135)
        elif cont_agencia >= 400:
            return "🟡 PRÓXIMO AGENCIA", QColor(249, 226, 175)
        elif not piso_hecho and cont_piso >= 225:
            return "🟡 PRÓXIMO PISO", QColor(249, 226, 175)
        elif not piso_hecho and cont_piso >= 200:
            return "🟢 PRÓXIMO PISO", QColor(166, 227, 161)
        elif piso_hecho:
            return "✅ PISO HECHO", QColor(137, 180, 250)
        else:
            return "🟢 OK", QColor(166, 227, 161)

    def buscar(self):
        termino = self.busqueda.text()
        if len(termino) < 2:
            self.cargar_datos()
            return

        datos = self.gestion.buscar(termino)
        self.tabla.setRowCount(len(datos))

        for i, row in enumerate(datos):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(row[1])))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"{row[3]:,}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{row[5]}/250"))
            self.tabla.setItem(i, 3, QTableWidgetItem(f"{row[6]}/500"))
            self.tabla.setItem(i, 4, QTableWidgetItem(str(row[7] if row[7] else "---")))
            self.tabla.setItem(i, 5, QTableWidgetItem(str(row[8] if row[8] else "---")))

            texto_checklist, color_checklist, tooltip = self.obtener_resumen_checklist(str(row[1]))
            item_checklist = QTableWidgetItem(texto_checklist)
            item_checklist.setForeground(QBrush(color_checklist))
            item_checklist.setToolTip(tooltip)
            item_checklist.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 6, item_checklist)

    def ver_detalles(self, tab_inicial=0):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un vehículo")
            return

        tha_id = self.tabla.item(row, 0).text()

        conn = sqlite3.connect(self.gestion.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tha_vehiculos WHERE tha_id = ?", (tha_id,))
        data = cursor.fetchone()
        conn.close()

        if data:
            dialog = DialogoVerVehiculo(data, self.imagen_tha, self.parent.db, self.tipo, tab_inicial, self)
            dialog.exec()
            self.cargar_datos()

    def registrar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un THA")
            return

        tha_id = self.tabla.item(row, 0).text()

        texto_horas = self.tabla.item(row, 1).text().replace(',', '')
        horas_actual = int(texto_horas)

        texto_piso = self.tabla.item(row, 2).text()
        if texto_piso == "✅ HECHO":
            cont_piso = 0
            manto_piso_hecho = True
        else:
            numeros = re.findall(r'\d+', texto_piso)
            cont_piso = int(numeros[0]) if numeros else 0
            manto_piso_hecho = False

        texto_agencia = self.tabla.item(row, 3).text()
        numeros_agencia = re.findall(r'\d+', texto_agencia)
        cont_agencia = int(numeros_agencia[0]) if numeros_agencia else 0

        dialog = DialogoRegistrarHorasTHA(tha_id, horas_actual, cont_piso, cont_agencia, manto_piso_hecho, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                exito, manto_piso, manto_agencia, error = self.gestion.registrar_horas(
                    tha_id, data['horas_nuevas'], data['fecha'], data['observaciones']
                )

                if exito:
                    self.cargar_datos()

                    if manto_agencia:
                        reply = QMessageBox.question(
                            self, "Mantenimiento Agencia",
                            f"🏢 {tha_id} ha alcanzado 500 horas.\n\n¿Registrar mantenimiento de AGENCIA?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._registrar_mantenimiento_agencia(tha_id)

                    elif manto_piso and not manto_piso_hecho:
                        reply = QMessageBox.question(
                            self, "Mantenimiento Piso",
                            f"✅ {tha_id} ha alcanzado 250 horas.\n\n¿Registrar mantenimiento de PISO?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            self._registrar_mantenimiento_piso(tha_id)

                    else:
                        QMessageBox.information(self, "Éxito", f"Registradas {data['horas_nuevas']} horas para {tha_id}")

    def _registrar_mantenimiento_piso(self, tha_id):
        for row in range(self.tabla.rowCount()):
            if self.tabla.item(row, 0) and self.tabla.item(row, 0).text() == tha_id:
                texto_piso = self.tabla.item(row, 2).text()
                if not texto_piso.startswith("✅"):
                    numeros = re.findall(r'\d+', texto_piso)
                    cont_piso = int(numeros[0]) if numeros else 0

                    dialog = DialogoMantenimientoPisoTHA(tha_id, cont_piso, self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        data = dialog.get_data()
                        if self.gestion.registrar_mantenimiento_piso(tha_id, data['fecha'], data['observaciones']):
                            self.cargar_datos()
                            QMessageBox.information(
                                self, "Éxito",
                                f"✅ Mantenimiento de PISO registrado para {tha_id} el {data['fecha']}"
                            )
                break

    def _registrar_mantenimiento_agencia(self, tha_id):
        for row in range(self.tabla.rowCount()):
            if self.tabla.item(row, 0) and self.tabla.item(row, 0).text() == tha_id:
                texto_piso = self.tabla.item(row, 2).text()
                if texto_piso.startswith("✅"):
                    cont_piso = 0
                else:
                    numeros = re.findall(r'\d+', texto_piso)
                    cont_piso = int(numeros[0]) if numeros else 0

                texto_agencia = self.tabla.item(row, 3).text()
                numeros_agencia = re.findall(r'\d+', texto_agencia)
                cont_agencia = int(numeros_agencia[0]) if numeros_agencia else 0

                dialog = DialogoMantenimientoAgenciaTHA(tha_id, cont_piso, cont_agencia, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    data = dialog.get_data()
                    if self.gestion.registrar_mantenimiento_agencia(tha_id, data['fecha'], data['observaciones']):
                        self.cargar_datos()
                        QMessageBox.information(
                            self, "Éxito",
                            f"🏢 Mantenimiento de AGENCIA registrado para {tha_id} el {data['fecha']}"
                        )
                break

    def editar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un THA")
            return

        tha_id = self.tabla.item(row, 0).text()
        texto_horas = self.tabla.item(row, 1).text().replace(',', '')
        horas_actual = int(texto_horas)

        dialog = DialogoEditarHorasTHA(tha_id, horas_actual, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                exito, mensaje = self.gestion.editar_horas(tha_id, data['nuevas_horas'], data['observaciones'])
                if exito:
                    self.cargar_datos()
                    QMessageBox.information(self, "Éxito", mensaje)

    def ver_historial(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un THA")
            return

        tha_id = self.tabla.item(row, 0).text()
        historial = self.gestion.obtener_historial(tha_id)

        if not historial:
            QMessageBox.information(self, "Info", "No hay historial para este THA")
            return

        dialog = DialogoHistorialTHA(tha_id, historial, self)
        dialog.exec()

    def agregar(self):
        dialog = DialogoAgregarTHA(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                if not data['tha_id'].startswith('THA-'):
                    QMessageBox.warning(self, "Error", "El ID debe comenzar con THA-")
                    return

                if self.gestion.agregar(data['tha_id'], data['horas'], data['observaciones']):
                    self.cargar_datos()
                    QMessageBox.information(self, "Éxito", f"THA {data['tha_id']} agregado")
                else:
                    QMessageBox.warning(self, "Error", f"El THA {data['tha_id']} ya existe")

    def eliminar(self):
        row = self.tabla.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Selecciona un THA")
            return

        tha_id = self.tabla.item(row, 0).text()

        reply = QMessageBox.question(self, "Confirmar", f"¿Eliminar {tha_id}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.gestion.eliminar(tha_id):
                self.cargar_datos()
                QMessageBox.information(self, "Éxito", f"THA {tha_id} eliminado")

# ============================================
# VENTANA PRINCIPAL
# ============================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        print("🚀 Iniciando aplicación...")

        self.db = BaseDatosVehiculos()
        self.exportador = ExportadorExcel(self.db.db_path)

        self.initUI()

        self.timer_backup = QTimer()
        self.timer_backup.timeout.connect(self.hacer_backup_automatico)
        self.timer_backup.start(3600000)

        QTimer.singleShot(2000, self.hacer_backup_inicial)

    def initUI(self):
        self.setWindowTitle("Sistema de Gestión de Flota - AK, AG y THA")
        self.setGeometry(100, 100, 1400, 650)

        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QWidget { background-color: #1e1e2e; color: #cdd6f4; }
            QTabWidget::pane {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #cdd6f4;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton#btnExportarAutomatico {
                background-color: #a6e3a1;
            }
            QPushButton#btnExportarManual {
                background-color: #f9e2af;
            }
            QTableWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                gridline-color: #45475a;
            }
            QHeaderView::section {
                background-color: #181825;
                padding: 8px;
                border: none;
                border-right: 1px solid #45475a;
                font-weight: bold;
                color: #89b4fa;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 5px;
                color: #cdd6f4;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("🚛 SISTEMA DE GESTIÓN DE FLOTA")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa; padding: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tab_ak = TablaAK(self)
        self.tab_ag = TablaAG(self)
        self.tab_tha = TablaTHA(self)

        self.tabs.addTab(self.tab_ak, "🚚 AKs (Kilómetros)")
        self.tabs.addTab(self.tab_ag, "⏱️ AGs (Horas)")
        self.tabs.addTab(self.tab_tha, "🔧 THA (Horas)")

        main_layout.addWidget(self.tabs)

        leyenda = QHBoxLayout()
        leyenda.addWidget(QLabel("Leyenda:"))

        colores = [
            ("🟢 OK", "#a6e3a1"),
            ("🟢 Próximo (80%)", "#a6e3a1"),
            ("🟡 Próximo (90%)", "#f9e2af"),
            ("🟠 Próximo Agencia (90%)", "#fab387"),
            ("🔴 Requiere", "#f38ba8"),
            ("✅ Piso Hecho", "#89b4fa")
        ]

        for texto, color in colores:
            label = QLabel(texto)
            label.setStyleSheet(f"color: {color}; font-weight: bold; margin-right: 15px;")
            leyenda.addWidget(label)

        leyenda.addStretch()
        main_layout.addLayout(leyenda)

        stats = QHBoxLayout()
        self.stats_total_ak = QLabel("Total AKs: 0")
        self.stats_total_ag = QLabel("Total AGs: 0")
        self.stats_total_tha = QLabel("Total THA: 0")
        self.stats_backup = QLabel("💾 Backup: cada hora")
        self.stats_ultimo_excel = QLabel("📊 Último Excel: ---")

        for label in [self.stats_total_ak, self.stats_total_ag, self.stats_total_tha, self.stats_backup, self.stats_ultimo_excel]:
            label.setStyleSheet("font-weight: bold; padding: 5px;")
            stats.addWidget(label)

        self.btn_exportar_manual = QPushButton("📥 Guardar Excel Manual")
        self.btn_exportar_manual.setMaximumWidth(180)
        self.btn_exportar_manual.clicked.connect(self.exportar_excel_manual)
        self.btn_exportar_manual.setStyleSheet("background-color: #f9e2af; color: #1e1e2e;")
        stats.addWidget(self.btn_exportar_manual)

        self.btn_exportar_auto = QPushButton("📤 Exportar Automático")
        self.btn_exportar_auto.setMaximumWidth(160)
        self.btn_exportar_auto.clicked.connect(self.exportar_excel_ahora)
        self.btn_exportar_auto.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e;")
        stats.addWidget(self.btn_exportar_auto)

        stats.addStretch()
        main_layout.addLayout(stats)

        self.actualizar_estadisticas()

    def actualizar_estadisticas(self):
        gestion_ak = GestionAK()
        gestion_ag = GestionAG()
        gestion_tha = GestionTHA()

        ak_data = gestion_ak.obtener_todos()
        ag_data = gestion_ag.obtener_todos()
        tha_data = gestion_tha.obtener_todos()

        self.stats_total_ak.setText(f"Total AKs: {len(ak_data)}")
        self.stats_total_ag.setText(f"Total AGs: {len(ag_data)}")
        self.stats_total_tha.setText(f"Total THA: {len(tha_data)}")

    def hacer_backup_inicial(self):
        exito, mensaje = self.db.backup_manager.hacer_backup("inicio")
        if exito:
            print(f"✅ Backup inicial realizado")
            self.exportar_excel_automatico("inicio")

    def hacer_backup_automatico(self):
        exito, mensaje = self.db.backup_manager.hacer_backup("automatico")
        if exito:
            print(f"✅ Backup automático realizado: {datetime.now().strftime('%H:%M')}")
            self.stats_backup.setText(f"💾 Último backup: {datetime.now().strftime('%H:%M')}")

    def exportar_excel_automatico(self, tipo="automatico"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"exportacion_{tipo}_{timestamp}.xlsx"

        file_path = os.path.join("excel_automatico", filename)

        exito, mensaje, ruta = self.exportador.exportar_todo(file_path)

        if exito:
            self.stats_ultimo_excel.setText(f"📊 Último Excel: {datetime.now().strftime('%H:%M')}")
            print(f"✅ Excel automático guardado: {filename}")
        return exito

    def exportar_excel_manual(self):
        nombre_sugerido = f"flota_vehiculos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel",
            nombre_sugerido,
            "Archivos Excel (*.xlsx)"
        )

        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'

            exito, mensaje, ruta = self.exportador.exportar_todo(file_path)

            if exito:
                QMessageBox.information(self, "Éxito", mensaje)

                self.stats_ultimo_excel.setText(f"📊 Último Excel manual: {datetime.now().strftime('%H:%M')}")

                reply = QMessageBox.question(
                    self,
                    "Abrir archivo",
                    "¿Deseas abrir el archivo Excel?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        os.startfile(file_path)
                    except:
                        try:
                            os.system(f'open "{file_path}"')
                        except:
                            try:
                                os.system(f'xdg-open "{file_path}"')
                            except:
                                QMessageBox.information(self, "Info", f"Archivo guardado en:\n{file_path}")
            else:
                QMessageBox.critical(self, "Error", mensaje)

    def exportar_excel_ahora(self):
        exito = self.exportar_excel_automatico("manual")
        if exito:
            QMessageBox.information(self, "Éxito", "Exportación automática completada")

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Confirmar salida",
            "¿Deseas hacer una copia de seguridad antes de salir?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db.backup_manager.hacer_backup("cierre")
            self.exportar_excel_automatico("cierre")
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            event.accept()
        else:
            event.ignore()

# ============================================
# MAIN
# ============================================
def main():
    app = QApplication(sys.argv)

    try:
        import pandas as pd
        import openpyxl
    except ImportError as e:
        print(f"❌ Error: Falta instalar dependencias: {e}")
        print("Instala con: pip install pandas openpyxl")
        QMessageBox.critical(
            None,
            "Error de dependencias",
            "Faltan librerías necesarias.\n\nEjecuta en terminal:\npip install pandas openpyxl"
        )
        sys.exit(1)

    for carpeta in ['backups', 'excel_automatico']:
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()