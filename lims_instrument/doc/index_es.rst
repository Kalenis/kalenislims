Módulo Lims Instrument
######################

Este módulo define la base para poder agregar importadores de resultados.
Un importador de resultados es un proceso capaz de leer determinado tipo de
archivo, extraer información e importarla en el sistema.
Los archivos que se procesan son usualmente de tipo CSV o XLS, generados por
instrumentos o equipos de laboratorio a partir de pruebas realizadas.


Importadores de resultados
**************************

En Lims > Configuración > Importadores de resultados se pueden definir y
listar un importador de resultados.
Estos importadores se definen en módulos específicos, que extienden a este.


Asistente para carga de resultados desde archivo
********************************************

Desde Lims > Laboratorio > Ingreso de resultados > Carga de resultados desde
archivo se puede lanzar el asistente de importación.

Es necesario definir un Importador de resultados y un archivo a ser importado.

