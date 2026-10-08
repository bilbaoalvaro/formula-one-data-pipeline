import pandas as pd
import requests
import time
from pathlib import Path
from typing import Optional

#Parametros que hemos tenido que añadir para que espera y funcione correctamente
DEFAULT_SLEEP_SECONDS = 1.0 
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 2.0


def request_json(url: str) -> Optional[dict]:
    """
    Realiza una petición GET con reintentos y backoff para evitar 429.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=15)
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                return None
            time.sleep(BASE_BACKOFF_SECONDS * attempt)
            continue

        if response.status_code == 429:
            # Rate limit: esperar y reintentar
            time.sleep(BASE_BACKOFF_SECONDS * attempt)
            continue

        if response.status_code != 200:
            return None

        try:
            return response.json()
        except ValueError:
            return None

    return None

def get_drivers_mapping(season: int) -> pd.DataFrame:
    """
    Obtiene la lista de pilotos y sus números para una temporada.
    """
    url = f"https://api.jolpi.ca/ergast/f1/{season}/drivers/?limit=1000"
    data = request_json(url)
    if not data:
        print(f"Error obteniendo datos de drivers para {season}")
        return pd.DataFrame(columns=["DriverId", "DriverNumber"])
    
    driver_numbers = {}
    
    for driver in data["MRData"]["DriverTable"]["Drivers"]:
        driver_id = driver.get("driverId")
        driver_number = driver.get("permanentNumber")
        
        if driver_id and driver_number:
            try:
                driver_numbers[driver_id] = int(driver_number)
            except:
                continue #Saltar números no válidos
    
    if not driver_numbers:
        return pd.DataFrame(columns=["DriverId", "DriverNumber"])
    
    df_drivers = (pd.DataFrame.from_dict(driver_numbers, orient="index", columns=["DriverNumber"]).reset_index().rename(columns={"index": "DriverId"}))
    
    return df_drivers


def get_pitstops(season: int, round_num: int) -> Optional[pd.DataFrame]:
    """
    Obtiene los pitstops de una carrera específica.
    """
    url = f"https://api.jolpi.ca/ergast/f1/{season}/{round_num}/pitstops/?limit=1000"
    data = request_json(url)
    if not data:
        print(f"Error obteniendo pitstops para {season} ronda {round_num}")
        return pd.DataFrame(columns=["DriverId", "NPitstops", "MedianPitStopDuration"])
    
    #Verifica si hay datos
    if not data["MRData"]["RaceTable"]["Races"]:
        return None
    
    races = data["MRData"]["RaceTable"]["Races"]
    pitstops = races[0].get("PitStops", [])
    
    if not pitstops:
        return pd.DataFrame(columns=["DriverId", "NPitstops", "MedianPitStopDuration"])
    
    df_pitstops = pd.DataFrame(pitstops)
    
    #Convertimos la duración a número
    df_pitstops["duration"] = pd.to_numeric(df_pitstops["duration"], errors="coerce")
    
    #Calculamos las estadísticas por cada piloto
    df_stats = (df_pitstops.groupby("driverId").agg(NPitstops=("duration", "size"),MedianPitStopDuration=("duration", "median")).reset_index().rename(columns={"driverId": "DriverId"}))
    
    return df_stats


def get_race_driver_numbers(season: int, round_num: int) -> Optional[pd.DataFrame]:
    """
    Obtiene el mapping DriverId -> DriverNumber para una carrera concreta.
    Usa los resultados de carrera para capturar cambios de numero (ej: campeon).
    """
    url = f"https://api.jolpi.ca/ergast/f1/{season}/{round_num}/results/?limit=1000"
    data = request_json(url)
    if not data:
        print(f"Error obteniendo resultados para {season} ronda {round_num}")
        return pd.DataFrame(columns=["DriverId", "DriverNumber"])

    races = data["MRData"]["RaceTable"]["Races"]
    if not races:
        return None

    results = races[0].get("Results", [])
    if not results:
        return pd.DataFrame(columns=["DriverId", "DriverNumber"])

    driver_numbers = {}
    for result in results:
        driver = result.get("Driver", {})
        driver_id = driver.get("driverId")
        driver_number = result.get("number")
        if driver_id and driver_number:
            try:
                driver_numbers[driver_id] = int(driver_number)
            except ValueError:
                continue

    if not driver_numbers:
        return pd.DataFrame(columns=["DriverId", "DriverNumber"])

    df_drivers = (
        pd.DataFrame.from_dict(driver_numbers, orient="index", columns=["DriverNumber"])
        .reset_index()
        .rename(columns={"index": "DriverId"})
    )
    return df_drivers


def merge_dataframes(df_drivers: pd.DataFrame, df_stats):
    """
    Combina los datos de pilotos con los pitstops.
    """
    if df_stats is None or df_stats.empty:
        df_stats = pd.DataFrame(columns=["DriverId", "NPitstops", "MedianPitStopDuration"])
    
    df_final = df_drivers.merge(df_stats, on="DriverId", how="left")
    
    #Rellenamos los valores vacíos
    df_final["NPitstops"] = df_final["NPitstops"].fillna(0).astype(int)
    
    #Ordenamos las columnas
    df_final = df_final[["DriverId", "DriverNumber", "NPitstops", "MedianPitStopDuration"]]
    
    return df_final


def process_all_seasons_races():
    """
    Procesa todas las temporadas desde 2019 hasta 2024.
    """
    start_year = 2019
    end_year = 2024
    
    print(f"Procesando temporadas del {start_year} al {end_year}:")
    print("-" * 40)
    
    for season in range(start_year, end_year + 1):
        print(f"\nTemporada {season}:")
        
        #Creamos una carpeta para la temporada
        season_folder = Path(str(season))
        season_folder.mkdir(exist_ok=True)
        
        #Obtenemos la lista de pilotos (fallback si falla el mapping por carrera)
        df_season_drivers = get_drivers_mapping(season)
        
        if df_season_drivers.empty:
            print(f"  No se encontraron datos de pilotos, por lo que salyamos la temporada")
            continue
        
        print(f"  Encontrados {len(df_season_drivers)} pilotos")
        
        #Procesamos cada carrera
        for race_round in range(1, 30):  #Máximo 30 carreras por temporada
            time.sleep(DEFAULT_SLEEP_SECONDS)  #Esperar entre peticiones para que no nos vuelva a dar fallo

            #Obtener mapping por carrera (numero real de ese GP)
            df_race_drivers = get_race_driver_numbers(season, race_round)
            if df_race_drivers is None:
                print(f"  No hay más carreras en esta temporada")
                break

            if df_race_drivers.empty:
                df_drivers = df_season_drivers.copy()
            else:
                df_drivers = df_race_drivers
                if not df_season_drivers.empty:
                    df_drivers = df_drivers.merge(
                        df_season_drivers,
                        on="DriverId",
                        how="left",
                        suffixes=("", "_season"),
                    )
                    if "DriverNumber_season" in df_drivers.columns:
                        df_drivers["DriverNumber"] = df_drivers["DriverNumber"].fillna(
                            df_drivers["DriverNumber_season"]
                        )
                        df_drivers = df_drivers.drop(columns=["DriverNumber_season"])
            
            #Obtener pitstops de esta carrera
            df_stats = get_pitstops(season, race_round)
            if df_stats is None:
                df_stats = pd.DataFrame(columns=["DriverId", "NPitstops", "MedianPitStopDuration"])
            
            #Combinamos los datos
            df_final = merge_dataframes(df_drivers, df_stats)
            
            #Guardamos el archivo
            filename = season_folder / f"race_{race_round:02d}.csv"
            df_final.to_csv(filename, index=False)
            
            # Mostramos el progreso
            drivers_with_pitstops = len(df_final[df_final["NPitstops"] > 0])
            print(f"    Carrera {race_round:02d}: {drivers_with_pitstops} pilotos con pitstops")
        
        print(f"  Temporada {season} completada")
    
    print("\n" + "=" * 40)
    print("Proceso completado!! Resumen de archivos generados:")
    
    # Mostrar resumen
    total_files = 0
    for season_folder in Path(".").glob("[0-9][0-9][0-9][0-9]"):  # Busca carpetas con 4 dígitos
        if season_folder.is_dir():
            files = list(season_folder.glob("race_*.csv"))
            if files:
                print(f"Temporada {season_folder.name}: {len(files)} carreras procesadas")
                total_files += len(files)
    
    print(f"\nTotal: {total_files} archivos CSV generados")


def main():
    """
    Punto de entrada para main.py.
    """
    process_all_seasons_races()


if __name__ == "__main__":
    main()
