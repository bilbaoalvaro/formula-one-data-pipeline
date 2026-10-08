import scrapy
import scrapy.http
import scrapy.http.request
import scrapy.http.response

import re
import pandas as pd
import io
import os


class F1ResultsSpider(scrapy.Spider):

    name = "f1_results"
    allowed_domains = ["wikipedia.org"]
    seasons = [2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    start_urls = ["https://en.wikipedia.org/"]

    def start_requests(self):
        for season in self.seasons:
            url = f"https://en.wikipedia.org/wiki/{season}_Formula_One_World_Championship"
            yield scrapy.Request(url, callback=self.parse, meta={"season": season})

    def parse(self, response):
        tabla = self.obtener_tabla_carreras(response)
        enlaces = self.obtener_links(tabla)
        carreras = self. obtener_rondas(tabla)
        yield from self.acceder_enlaces(response, enlaces, response.meta["season"], carreras)

    def report_parse(self, response):
        tabla = self.obtener_tabla_clasificacion(response)
        df = pd.read_html(io.StringIO(tabla))[0]
        df["ronda"] = response.meta["ronda"]
        df["nombre_carrera"] = response.meta["nombre"]
        df = df.iloc[:-2]
        self.crear_archivos(response.meta["season"], df, response.meta["ronda"])



    def obtener_tabla_carreras(self, response: scrapy.http.response):
        return response.xpath('//table[.//span[normalize-space()="Report"]]')[0]
    
    def obtener_tabla_clasificacion(self, response):
        return response.css("table.wikitable").get()
    
    def obtener_rondas(self, tabla):
        #Obtenemos los headers
        tr_head = tabla.xpath(".//tr")[0]
        ths = tr_head.xpath(".//th").getall()

        #Sacamos indice de columna report
        

        name_indice = -1
        for th in ths:
            if "Grand Prix" in th:
                break
            name_indice += 1

        filas = tabla.xpath(".//tr")
        
        carreras = []
        #Extraemos celdas name y round por fila y su enlace
        for i, fila in enumerate(filas):
            if i == 0 or i == len(filas) -1:
                continue
            tds = fila.xpath(".//td")
            td_name = tds[name_indice]
            texto = td_name.xpath(".//a/text()").get()
            carreras.append([i, texto])
        return carreras

    def obtener_links(self, tabla):
        #Obtenemos los headers
        tr_head = tabla.xpath(".//tr")[0]
        ths = tr_head.xpath(".//th").getall()

        #Sacamos indice de columna report
        reports_indice = -1
        for th in ths:
            if "Report" in th:
                break
            reports_indice += 1

        #Sacamos
        filas = tabla.xpath(".//tr")

        enlaces = []
        #Extraemos celda report por fila y su enlace
        patron_enlace = re.compile(r'href="([^"]*)"')
        for fila in filas:
            tds = fila.xpath(".//td")
            if len(tds) > reports_indice:
                td_enlace = tds[reports_indice].get()
                enlace = patron_enlace.search(td_enlace).group(1)
                enlaces.append(enlace)
        return enlaces

    def acceder_enlaces(self, response, enlaces, season, carreras):
        for i, enlace in enumerate(enlaces):
            yield response.follow(enlace, callback=self.report_parse, meta={"season": season, "ronda": carreras[i][0], "nombre": carreras[i][1]})

    def crear_archivos(self, season, df: pd.DataFrame, ronda):
        os.makedirs(f"data/season_{season}", exist_ok=True)
        df.to_csv(f"data/season_{season}/ronda_{ronda}.csv")
        

        