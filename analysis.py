from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def preparar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    #Columnas que voy a utilizar para los graficos en formato numerico
    if "Pos." in df.columns:
        df["Pos_numeric"] = pd.to_numeric(df["Pos."], errors="coerce")
    else:
        df["Pos_numeric"] = np.nan

    if "Final grid" in df.columns:
        df["Final_grid_numeric"] = pd.to_numeric(df["Final grid"], errors="coerce")
    else:
        df["Final_grid_numeric"] = np.nan

    if "NPitstops" in df.columns:
        df["NPitstops_numeric"] = pd.to_numeric(df["NPitstops"], errors="coerce")
    else:
        df["NPitstops_numeric"] = np.nan

    if "MedianPitStopDuration" in df.columns:
        df["MedianPitStopDuration_numeric"] = pd.to_numeric(df["MedianPitStopDuration"], errors="coerce")
    else:
        df["MedianPitStopDuration_numeric"] = np.nan

    return df



def dibuja_salida_vs_resultado(df: pd.DataFrame, direccion: Path) -> float: #comparamos pos salida vs pos final
    work = df[["Final_grid_numeric", "Pos_numeric"]].dropna().copy()

    correlacion = work["Final_grid_numeric"].corr(work["Pos_numeric"])

    plt.figure()
    plt.scatter(work["Final_grid_numeric"], work["Pos_numeric"], s=10, alpha=0.5)
    plt.xlabel("Posición de salida (Final grid)")
    plt.ylabel("Posición final (Pos.)")
    plt.title(f"Posición de salida vs posición final (correlacion={correlacion:.3f})") #3 decimales para que no sea muy largo el número
    plt.gca().invert_yaxis()  #El 1 es mejor
    plt.tight_layout()
    plt.savefig(direccion / "salidavsresultado.png", dpi=200)
    plt.close()

    return float(correlacion)



def dibuja_top10_constructores(df: pd.DataFrame, direccion: Path) -> pd.Series: #dibujamos top 10 constructores
    work = df[["Constructor", "Pos_numeric"]].dropna().copy() #Eliminamos los nulos

    ranking = work.groupby("Constructor")["Pos_numeric"].mean().sort_values() 
    top10 = ranking.head(10) #Ordenamos por constructor y hacemos la media de la posición final y cogemos los 10 primeros

    plt.figure()
    top10.plot(kind="bar")
    plt.xlabel("Constructor")
    plt.ylabel("Posición media final (menor es mejor)")
    plt.title("Top 10 constructores por posición media final")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(direccion / "top10constructores.png", dpi=200)
    plt.close()

    return top10



def dibuja_media_posicion_por_paradas(df: pd.DataFrame, direccion: Path) -> pd.Series: #Media posicion por número de parada
    work = df[["NPitstops_numeric", "Pos_numeric"]].dropna().copy()

    #Por si hay decimales porque yo lo necesito en int redondeo
    work["NPitstops_int"] = work["NPitstops_numeric"].round().astype(int)

    #Ordeno por nº de paradas y luego en la columna de la posición hago la media
    media_por_paradas = work.groupby("NPitstops_int")["Pos_numeric"].mean().sort_index()

    plt.figure()
    media_por_paradas.plot(kind="bar")
    plt.xlabel("Número de pit stops")
    plt.ylabel("Posición media final (menor es mejor)")
    plt.title("Posición media final según nº de paradas")
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(direccion / "num_paradas.png", dpi=200)
    plt.close()

    return media_por_paradas


def dibuja_duracion_pitstop_vs_posicion(df: pd.DataFrame, direccion: Path) -> float: #Correlacion entre duracion pit stop y pos final
    work = df[["MedianPitStopDuration_numeric", "Pos_numeric"]].dropna().copy()

    x = work["MedianPitStopDuration_numeric"]
    y = work["Pos_numeric"]

    correlacion = x.corr(y)

    plt.figure()
    plt.scatter(x, y, s=10, alpha=0.4)
    plt.xlabel("Duración mediana del pit stop (s)")
    plt.ylabel("Posición final (Pos.)")
    plt.title(f"Duración pit stop vs posición final (correlacion={correlacion:.3f})")
    plt.gca().invert_yaxis()

    #Voy a añadir una línea de tendencia para hacer más evidente la relación entre las variables
    if len(work) > 2:
        m, b = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 120)
        plt.plot(xs, m * xs + b, linewidth=2)

    plt.tight_layout()
    plt.savefig(direccion / "duracion_paradas.png", dpi=200)
    plt.close()

    return float(correlacion)


def main(df: pd.DataFrame, direccion: str = "Graficas") -> dict: #Función que genera las gráficas que hemos definido antes
    carpeta_salida = Path(direccion)
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    df = preparar_dataframe(df)

    resultados = {
        "corr_salida_resultado": dibuja_salida_vs_resultado(df, carpeta_salida),
        "top10_constructores": dibuja_top10_constructores(df, carpeta_salida),
        "media_posicion_por_paradas": dibuja_media_posicion_por_paradas(df, carpeta_salida),
        "corr_duracion_posicion": dibuja_duracion_pitstop_vs_posicion(df, carpeta_salida),
        "direccion": str(carpeta_salida),
    }

    return resultados
