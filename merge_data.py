import pandas as pd
from pathlib import Path
import re


def load_scrapy_data(file_path: Path) -> pd.DataFrame:
    """
    Carga los datos del CSV generado por Scrapy.
    """
    try:
        df = pd.read_csv(file_path)
        
        #Verificamos si el DataFrame está vacío o tiene muy pocas filas
        if df.empty or len(df) < 2:
            print(f"Archivo vacío o con datos insuficientes: {file_path.name}")
            return None
        
        #El CSV de Scrapy tiene un índice sin nombre en la primera columna
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])

        #Eliminamos las filas que repiten el header dentro del CSV
        if 'Pos.' in df.columns:
            df = df[df['Pos.'].astype(str).str.strip().str.lower() != 'pos.']
        if 'Driver' in df.columns:
            df = df[df['Driver'].astype(str).str.strip().str.lower() != 'driver']
        if 'Car no.' in df.columns:
            df = df[df['Car no.'].astype(str).str.strip().str.lower() != 'car no.']
        
        #La columna con el número del piloto varía según la tabla
        columns_lower = {col.lower(): col for col in df.columns}
        number_col = None
        for candidate in ["no.", "car no.", "car no", "car number"]:
            if candidate in columns_lower:
                number_col = columns_lower[candidate]
                break

        if number_col:
            df['DriverNumber'] = pd.to_numeric(df[number_col], errors='coerce')
        elif 'Driver' in df.columns:
            #Fallback: intentar extraer del nombre si No. no existe
            df['DriverNumber'] = df['Driver'].apply(
                lambda x: extract_driver_number(x) if pd.notna(x) else None
            )
        else:
            print(f"No se encontró columna 'No.' ni 'Driver' en {file_path.name}")
            return None
        
        # Eliminar filas sin número de piloto válido
        df = df.dropna(subset=['DriverNumber'])
        
        if df.empty:
            print(f"No hay pilotos con número válido en {file_path.name}")
            return None
        
        return df
        
    except Exception as e:
        print(f"Error encontrado cargando {file_path}: {e}")
        return None


def extract_driver_number(driver_name: str) -> int:
    """
    Extrae el número del piloto del nombre (fallback).
    Formatos esperados: "1 Max Verstappen" o "44 Lewis Hamilton"
    """
    if pd.isna(driver_name):
        return None
    
    match = re.match(r'^(\d+)\s+', str(driver_name).strip())
    if match:
        return int(match.group(1))
    return None


def load_api_data(file_path: Path) -> pd.DataFrame:
    """
    Carga los datos del CSV generado desde la API.
    """
    try:
        df = pd.read_csv(file_path)
        
        if df.empty:
            print(f"Archivo API etsa vacío: {file_path.name}")
            return None
        
        # Asegurar que DriverNumber sea numérico
        df['DriverNumber'] = pd.to_numeric(df['DriverNumber'], errors='coerce')
        
        return df
        
    except Exception as e:
        print(f"Error encontrado al cargar {file_path}: {e}")
        return None


def merge_race_data(scrapy_df: pd.DataFrame, api_df: pd.DataFrame, 
                    season: int, race_number: int) -> pd.DataFrame:
    """
    Fusiona los datos de Scrapy y la API para una carrera específica.
    """
    if scrapy_df is None or scrapy_df.empty:
        return None
    
    if api_df is None or api_df.empty:
        return None
    
    #Aseguramos que DriverNumber sea int en ambos DataFrames
    scrapy_df['DriverNumber'] = scrapy_df['DriverNumber'].astype(int)
    api_df['DriverNumber'] = api_df['DriverNumber'].astype(int)
    
    #Merge mediante DriverNumber
    merged_df = scrapy_df.merge(
        api_df[['DriverId', 'DriverNumber', 'NPitstops', 'MedianPitStopDuration']],
        on='DriverNumber',
        how='left'
    )
    
    #Añadimos columnas de identificación
    merged_df['Season'] = season
    merged_df['RaceNumber'] = race_number
    
    #Reorganizamos columnas: Season y RaceNumber al principio
    cols = merged_df.columns.tolist()
    priority_cols = ['Season', 'RaceNumber']
    other_cols = [col for col in cols if col not in priority_cols]
    merged_df = merged_df[priority_cols + other_cols]
    
    return merged_df


def process_all_seasons(start_year: int = 2019, end_year: int = 2024):
    """
    Procesa todas las temporadas y genera un DataFrame consolidado.
    """
    all_data = []
    
    print(f"Procesando temporadas del {start_year} al {end_year}...")
    print("=" * 60)
    
    for season in range(start_year, end_year + 1):
        # Rutas de carpetas
        api_folder = Path(str(season))
        scrapy_folder = Path(f"data/season_{season}")
        
        # Verificar que existan ambas carpetas
        if not api_folder.exists():
            print(f"\nCarpeta API {season}/ no encontrada, saltando...")
            continue
        
        if not scrapy_folder.exists():
            print(f"\nCarpeta Scrapy data/season_{season}/ no encontrada, saltando...")
            continue
        
        print(f"\n Temporada {season}:")
        
        # Buscar archivos de API
        api_files = sorted(api_folder.glob("race_*.csv"))
        
        if not api_files:
            print(f"No se encontraron archivos de API")
            continue
        
        print(f"Encontrados {len(api_files)} archivos de API")
        
        # Procesar cada carrera
        race_count = 0
        for api_file in api_files:
            # Extraer número de ronda del nombre del archivo
            match = re.search(r'race_(\d+)', api_file.name)
            if not match:
                continue
            
            race_number = int(match.group(1))
            
            # Buscar archivo correspondiente de Scrapy
            scrapy_file = scrapy_folder / f"ronda_{race_number}.csv"
            
            if not scrapy_file.exists():
                print(f"No existe ronda_{race_number}.csv")
                continue
            
            # Cargar datos
            api_df = load_api_data(api_file)
            scrapy_df = load_scrapy_data(scrapy_file)
            
            # Verificar que ambos DataFrames sean válidos
            if api_df is None or scrapy_df is None:
                continue
            
            # Fusionar datos
            merged_df = merge_race_data(scrapy_df, api_df, season, race_number)
            
            if merged_df is not None and not merged_df.empty:
                all_data.append(merged_df)
                race_count += 1
                
                # Estadísticas de la carrera
                total_drivers = len(merged_df)
                drivers_with_pitstops = (merged_df['NPitstops'] > 0).sum()
                matched_drivers = merged_df['DriverId'].notna().sum()
                
                print(f"Carrera {race_number:02d}: {total_drivers} pilotos, "
                      f"{matched_drivers} matcheados con API, "
                      f"{drivers_with_pitstops} con pitstops")
        
        print(f"  📊 Total temporada: {race_count} carreras procesadas")
    
    # Consolidar todos los datos
    if not all_data:
        print("\n" + "=" * 60)
        print("No se encontraron datos para consolidar")
        print("\nDiagnóstico:")
        print("Verifica la estructura de carpetas:")
        print(" -> API: 2019/race_01.csv, 2019/race_02.csv, ...")
        print(" -> Scrapy: data/season_2019/ronda_1.csv, data/season_2019/ronda_2.csv, ...")
        return None
    
    print("\n" + "=" * 60)
    print("Concateno los datos:")
    
    final_df = pd.concat(all_data, ignore_index=True)
    
    print(f"DataFrame final creado, hay {len(final_df)} registros totales")
    print(f"  -> Temporadas: {final_df['Season'].nunique()}")
    print(f"  -> Carreras únicas: {len(final_df.groupby(['Season', 'RaceNumber']))}")
    
    if 'Driver' in final_df.columns:
        print(f"  -> Pilotos únicos: {final_df['Driver'].nunique()}")
    
    # Estadísticas de matching
    total_with_api = final_df['DriverId'].notna().sum()
    match_rate = (total_with_api / len(final_df)) * 100
    print(f"  -> Registros con datos de API: {total_with_api}/{len(final_df)} ({match_rate:.1f}%)")
    
    return final_df


def export_final_dataset(df: pd.DataFrame, output_path: str = "f1_complete_dataset.csv"):
    """
    Exporta el DataFrame final a CSV.
    """
    if df is None or df.empty:
        print("No hay datos para exportar")
        return
    
    try:
        df.to_csv(output_path, index=False)
        file_size = Path(output_path).stat().st_size / 1024
        
        print(f"\nDataset exportado exitosamente: {output_path}")
        print(f"Tamaño del archivo: {file_size:.2f} KB")
        
        #Mostrar información del dataset
        print(f"\nInformación del dataset:")
        print(f"   Dimensiones: {len(df)} filas x {len(df.columns)} columnas")
        
        print(f"\n   Columnas disponibles:")
        for col in df.columns:
            non_null = df[col].notna().sum()
            percentage = (non_null / len(df)) * 100
            print(f"     • {col}: {non_null}/{len(df)} ({percentage:.1f}%)")
        
        #Estadísticas de pitstops
        if 'NPitstops' in df.columns:
            pitstops_data = df[df['NPitstops'] > 0]
            print(f"\n     Estadísticas de Pitstops:")
            print(f"     • Registros con pitstops: {len(pitstops_data)}/{len(df)}")
            print(f"     • Media de pitstops: {df['NPitstops'].mean():.2f}")
            print(f"     • Máximo de pitstops en una carrera: {df['NPitstops'].max():.0f}")
        
        if 'MedianPitStopDuration' in df.columns:
            valid_durations = df['MedianPitStopDuration'].dropna()
            if len(valid_durations) > 0:
                print(f"     • Duración mediana promedio: {valid_durations.mean():.3f}s")
                print(f"     • Pitstop más rápido: {valid_durations.min():.3f}s")
                print(f"     • Pitstop más lento: {valid_durations.max():.3f}s")
        
    except Exception as e:
        print(f"Error al exportar: {e}")


def show_sample_data(df: pd.DataFrame, n_rows: int = 5):
    """
    Muestra una muestra de los datos procesados.
    """
    if df is None or df.empty:
        return
    
    print(f"\nMuestra de los datos (primeras {n_rows} filas):")
    print("=" * 60)
    
    # Seleccionar columnas más relevantes para mostrar
    important_cols = ['Season', 'RaceNumber', 'Driver', 'Constructor', 
                     'Pos.', 'DriverNumber', 'NPitstops', 
                     'MedianPitStopDuration', 'DriverId']
    
    display_cols = [col for col in important_cols if col in df.columns]
    
    if display_cols:
        sample = df[display_cols].head(n_rows)
        print(sample.to_string(index=False))
    else:
        print(df.head(n_rows).to_string(index=False))


def main():
    """
    Función principal que ejecuta todo el proceso de fusión.
    """
    print("F1 Data Merger")
    print("=" * 60)
    print("Fusiona datos de Scrapy (Wikipedia) y API (Jolpica)")
    print()
    
    # Procesar todas las temporadas
    final_df = process_all_seasons(start_year=2019, end_year=2024)
    
    # Si hay datos, exportar y mostrar muestra
    if final_df is not None:
        export_final_dataset(final_df)
        show_sample_data(final_df, n_rows=10)
        
        print("\n" + "=" * 60)
        print("Proceso completado exitosamente")
        print(f"Archivo generado: f1_complete_dataset.csv")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("No se pudo generar el dataset final")
        print("\nChecklist:")
        print("  1.  Ejecutar spider Scrapy → genera data/season_XXXX/ronda_X.csv")
        print("  2.  Ejecutar api_f1.py → genera XXXX/race_XX.csv")
        print("  3.  Verificar que los números de ronda coincidan")
        print("=" * 60)


if __name__ == "__main__":
    main()
