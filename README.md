# Dashboard de Acciones

## Narrativa

En la actualidad, el desarrollo de aplicaciones modernas es posible en parte, gracias a la integración de múltiples tecnologías que trabajan de manera conjunta, como es el caso de las infinidades de APIs disponibles, la inteligencia artificial, distintos frameworks de desarrollo, y mucho más. Volviendo a la inteligencia artificial y en especial a los LLMs, han visto un salto dramático en los últimos años, y aun con sus limitaciones y problemas, si se trabajan de forma óptima, pueden brindar excelentes resultados en muchísimas áreas.

Este proyecto se centra en la capacidad de entender el estado de una empresa a partir del uso de distintas técnicas. El sistema tiene la forma de un dashboard interactivo, en donde el usuario puede ingresar el ticker o símbolo bursátil de una empresa, y se devuelven históricos de precios en distintos periodos, indicadores técnicos clásicos con estados, un conjunto de noticias recientes relacionadas, y un resumen de la empresa generado por un modelo de inteligencia artificial. Además, se cuenta con un historial de los tickers consultados.

El objetivo último del proyecto es lograr consolidar la información relevante de una empresa en una interfaz moderna y responsiva, que facilite el estudio de la empresa por parte del usuario.

## Requerimientos Funcionales

+ El sistema debe permitir ingresar un símbolo bursátil y consultar los datos históricos de precios asociados en el periodo de un año.
+ El sistema debe ser capaz de mostrar un gráfico con la evolución del precio para distintos intervalos (1 día, 1 mes, 1 año, inicio de año y máximo).
+ El sistema debe ser capaz de calcular e indicar el estado de los principales indicadores técnicos (SMA 10, SMA 50, SMA 200, MACD, Estocástico, RSI, Volatilidad).
+ El sistema debe ser capaz de listar las últimas noticias financieras del activo consultado, incluyendo título, fuente y enlace.
+ El sistema debe ser capaz de generar un resumen automático del activo utilizando el modelo de inteligencia artificial Gemini.
+ El sistema debe permitir visualizar el detalle de una noticia y abrir el enlace en el navegador.
+ El sistema debe mantener un historial de tickets consultados de forma persistente y permitir volver a consultarlos.
+ El sistema debe permitir limpiar el historial de tickets mediante un botón dedicado
+ El sistema debe notificar al usuario en caso de errores al obtener datos o generar el resumen.

## Requerimientos No Funcionales

+ El sistema debe ejecutarse desde un único archivo principal denominado main.py.
+ El sistema debe ser desarrollado utilizando Python y PyQt6.
+ El sistema debe funcionar correctamente sin errores de compatibilidad en equipos con Windows 10 (o superior), macOS o Linux.
+ El sistema debe funcionar fluidamente en un equipo hogareño estándar.
+ El sistema debe manejar errores sin interrumpir la ejecución de la aplicación.
+ El sistema debe responder a las consultas con una latencia menor a 5 segundos en equipos estándar.

## Stack Tecnológico

Todo el sistema se ha realizado en **Python + PyQt6** debido al conocimiento y experiencia en el manejo de los mismo por parte de los integrantes y al uso local de los distintos sistemas.

Para la búsqueda de los datos de las acciones de una empresa y la obtención de las noticias más recientes de la misma se recurrió a la API de **yfinance**.

Para los gráficos de precios se utiliza **pandas** para limpiar los datos obtenidos, y luego **pyqtgraph** para graficarlos.

Para la generación de los indicadores técnicos implementados también se utiliza **pandas** para transformar los datos obtenidos, de manera que puedan ser utilizados para diversos cálculos.

El modelo de IA que se usa para la generación de resúmenes es **Gemini 2.5 Flash**, debido a que permite, en su versión gratis, una cantidad de **requests por minuto (RPM), tokens por minuto (TPM) y requests por día (RPD)**, que es aceptable para este proyecto. Comparando con otros modelos Gemini:

| **Modelo**         | **RPM**         | **TPM**                      | **RPD** |
| :---------------------: | :----------: | :----------: | :----------:
| Gemini 2.5 Pro | 5 | 250.000  | 100 |
| **Gemini 2.5 Flash** | **10** | **250.000**  | **250** |
| Gemini 2.5 Flash Lite | 15 | 250.000  | 1000 |

La lista completa de librerias utilizadas en el proyecto se puede encontrar en el archivo [requirements.txt](https://github.com/oldaniMarcos/TPI-Soporte/blob/main/requirements.txt)

## Uso de Base de Datos

El sistema hace uso de **SQLite + SQLAlchemy** para preservar el historial de tickers consultados, dada la dinámica del sistema no es necesario almacenar mas datos, ya que requiere que todos estén actualizados. El modelo de dominio es el siguiente:

<img width="162" height="82" alt="Diagrama sin título drawio" src="https://github.com/user-attachments/assets/84254e7b-f355-4ed3-8470-858004b19b7a" />

## Calculos

### Promedio móvil simple

Nos provee de la tendencia de las acciones, suavizando las fluctuaciones.
Dentro del programa hacemos uso de la función .rolling(window) proporcionada por la librería **pandas** para varios cálculos. En este caso se usó rolling(window = periodo).mean para el cálculo del promedio móvil simple (PMS) para los períodos 10, 50, 200.

Para proporcionarle un estado lo calificamos según el precio de la última acción y el último valor del PMS[-1] de la siguiente forma:

+ PMS ≈ Precio_Cierre → **Neutral (Posible cambio de tendencia)**
+ PMS < Precio_Cierre → **Good (Tendencia positiva)**
+ PMS > Precio_Cierre → **Bad (Tendencia negativa)**

### MACD

El **MACD (Moving Average Convergence/Divergence)** es un indicador de momentum que mide la relación entre dos medias móviles exponenciales (EMA) para detectar cambios en la fuerza, dirección y duración de una tendencia. Los periodos de las medias móviles exponenciales seleccionadas fueron 12 y 26 y para la línea de señal es 9.

Para el cálculo de la línea de señal se usó la función .ewm(span=periodo_señal) de la librería **pandas**.

El MACD es calculado como EMA_Corto - EMA_Largo y el Histograma como MACD - Signal_Line

Las condiciones para asignarle un estado fue la siguiente:

+ MACD > Signal_Line → **Good (señal alcista)**
+ MACD < Signal_Line → **Bad (señal bajista)**
+ Histograma ≈ 0 → **Neutral (el mercado no tiene una dirección clara)**

### Oscilador estocástico

Es un indicador de momentum que compara el precio de cierre de una acción con su rango de precios (máximo/mínimo) durante un período específico, que en este caso es de 14. Su objetivo es identificar condiciones de sobrecompra y sobreventa.
Obtenemos el PMS(14) para los mínimos y máximo y se calculó el %K (Lineal Rápida) con la siguiente fórmula:

%k = (Cierre - Minₙ) / (Maxₙ - Minₙ)

y el %D (Línea Lenta) que es igual al SMA(3) de los precios de cierre.
La interpretación de los parámetros fue la siguiente:

1. %K > %D and %K_prev <= %D_prev
  + %K > 80% → bad (Riesgo de corrección)
  + %K <= 80% → good (señal de compra)
2. %K < %D and %K_prev >= %D_prev
  + %K < 20% → neutral (advertencia de sobrevendido)
  + %K >= 20% → bad (Señal de venta)
3. %K > 80% → bad (Riesgo de regresión)
4. %K < 20% → good (Posible rebote hacia creciente)
5. 20% < %K < 80% → ninguno (Mantener posición)

### RSI

El **RSI (Relative Strength Index)** es un indicador de momentum que mide la velocidad y el cambio de los movimientos del precio. Es una herramienta clave para identificar activos sobrecomprados y sobrevendidos.
Para el cálculo del RSI tenemos que calcular el gain y el loss. Para ello calculamos la diferencia entre cada elemento y su anterior en la lista de precios de cierre y lo denominamos “delta”. Para el cálculo de gain se calculó el PMS(14) de los valores positivos y un PMS(14) de los valores negativos para el loss. El RSI se calculó como:

RS = Gain / Loss  
RSI = 100 - 100 / (1 + RS)

La interpretación que le dimos al RSI es la siguiente:

+ RSI < 30% → Good (rebote al alza)
+ RSI > 70% → Bad (corrección a la baja)
+ 30% <= RSI <= 70% → Ninguno (mantener la posición)

### Volatilidad

Es una medida de riesgo que cuantifica cuánto se espera que varíe el precio de un activo durante un período de tiempo.
Para obtener la volatilidad calculamos el retorno logarítmico de la siguiente forma:

RetLn = ln(PT / PT₋₁)  
Volatilidad = Desv.Std. de RetLn × √252

La interpretación que le dimos a la Volatilidad (V) es la siguiente:
V < 15% → Ninguno (Estabilidad extrema)
V > 30% → Bad (Riesgo elevado)
15% <= V <= 30% → Neutral (Riesgo moderado)

### ATR

El **ATR (Average True Range)** es un indicador técnico desarrollado por J. Welles Wilder que mide la volatilidad real del mercado.
Considera los gaps y las variaciones entre los precios máximos y mínimos diarios, ofreciendo una visión más completa del rango real de movimiento del activo.

Para su cálculo, se determina primero el True Range (TR) de cada período como el máximo de los siguientes tres valores:

+ TR₁ = High − Low
+ TR₂ = |High − Close₍ₜ₋₁₎|
+ TR₃ = |Low − Close₍ₜ₋₁₎|

Luego, el ATR se obtiene como el promedio móvil simple del TR durante un período (se ha utilizado uno de 14 días):

+ ATR = Promedio(TR₁₄)

La interpretación que le dimos al ATR es la siguiente:

+ ATR < 1 → Ninguno (Baja volatilidad real)
+ ATR > 5 → Bad (Alta volatilidad real)
+ 1 <= ATR <= 5 → Neutral (Volatilidad moderada)

## Casos de Uso

Se pueden encontrar en [el siguiente link](https://github.com/oldaniMarcos/TPI-Soporte/blob/main/Casos%20de%20Uso.pdf)

