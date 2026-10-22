from sikorius.importador import importar_datos

df = importar_datos("data/prueba.csv")
print(df.head())
print(df.dtypes)