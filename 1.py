import pandas as pd

ruta = "/Users/potaito/Documents/entorno/Check list IQ validación de proceso soplado v1.xlsx"

df = pd.read_excel(ruta)

print(df.head())