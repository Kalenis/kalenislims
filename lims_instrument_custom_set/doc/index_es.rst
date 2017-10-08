Módulo Lims Instrument Custom Set
#################################

Este módulo define dos importadores de resultados:
-Planilla personalizada - CSV (no implementada aún)
-Planilla personalizada - XLS

Se trata en ambos casos de planillas definidas por el usuario, sin relación
con archivos exportados por un instrumento particular.


Planilla personalizada - XLS
****************************

Este importador es capaz de interpretar una planilla de Excel a partir de
ciertos parámetros que puede definir el usuario, es decir que no responden al
esquema de ningún instrumento o equipo.

Utiliza la librería 'xlrd' para extraer la información de las planillas Excel:
http://www.python-excel.org/

Los parámetros que es necesario definir en cada hoja son:

- 'Analysis Code': indica el código del análisis al que corresponden los
valores expuestos en la hoja. Si en una celda se pone 'Analysis Code', en la
celda que esté a su derecha se buscará el código del análisis.

- 'Data Header': si se indica este valor en una celda, el importador buscará
en la fila inmediata inferior la cabecera de los valores que se
pretende ingresar.
De esta cabecera, las cuatro primeras columnas deben corresponder a:
    - Muestra
    - Año
    - Fracción
    - Repetición
    
Sin importar cuáles sean los nombres definidos para esas columnas, los cuatro
valores se harán corresponder, en ese orden, con esos datos, que son los que
permiten identificar una línea de cuaderno.
De ahí en más, las restantes columnas pueden corresponder a cualquier valor
que determine el usuario, sin límites.
Para los nombres de las columnas pueden utilizarse espacios y puntos, pero se
recomienda evitar cualquier caracter que pueda confundirse con una fórmula o
expresión algebráica, por ejemplo: / + - ( ) *
También es preferible no utilizar caracteres no ASCII, ya que el parseador
de fórmulas pueden rechazarlo por inválido e ignorarlo.

- 'Formula': a la derecha de aquella celda que contenga el valor 'Formula' se
deberá definir la fórmula de cálculo.
Para que la fórmula pueda ser correctamente mapeada, las variables deben
coincidir con el nombre de alguna de las columnas cabecera definidas como
'Data Header'.
La cabecera puede contener columnas que no son utilizadas en la fórmula, pero
para que la fórmula se aplique correctamente todas sus variables deben estar
representadas en la cabecera.

Si al analizar la hoja no se pueden determinar estos tres parámetros (
'Analysis Code', 'Data Header' y 'Formula'), el importador de datos concluirá
la lectura sin tomar datos.

Hay un último valor, opcional, que tiene una función especial:
- '###': si se pone ### en la primera celda (A1), la hoja es ignorada; puede
ser útil si se desea que una hoja no sea tenida en cuenta durante la
importación.


Carga de datos
**************
Para empezar a cargar valores es necesario copiar la cabecera definida como
'Data Header' y en las filas que siguen cargar los datos.
Los datos deben ser númericos y deben existir (no pueden dejarse vacíos).

Si alguna fila se deja en blanco, el importador de datos continuará con las
siguientes hasta volver a encontrar otra vez la cabecera, circunstancia en la
cual continuará con la captación de valores.

Si ya no se encuentra la cabecera, la lectura seguirá sin captar valores,
hasta llegar al final de la hoja. Una vez concluida una hoja se sigue con la
siguiente.

En distintas hojas de la planilla de cálculo se puede hacer referencia a la
misma fracción, quizá con un análisis distinto.
