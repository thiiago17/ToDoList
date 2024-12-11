# TO DO LIST

- Antes de iniciar la aplicacion hay que crear una variable SECRET_KEY en el archivo config.py. De lo contrario, la aplicacion no funcionara
- El archivo SQL contiene 4 tablas basicas para el funcionamiento de la web. Una de ellas es la tabla usuarios que contiene 3 usuarios creados, cada uno con un rol distinto, para poder observar todas las funciones existentes.

## Funciones

- Login y creacion de usuario
- Seccion principal donde se pueden agregar tareas junto a su prioridad y a su vez visualizar aquellas pendientes
- Opciones de borrar tareas pendientes (borrado logico), marcarlas como terminadas y compartir con otros mediante un QR
- Opcion de exportar las tareas pendientes a un archivo de excel
- Seccion reportes, donde hay 3 tipos de graficos distintos. Uno para las tareas pendientes, donde se muestra cuantas tareas pendientes hay en cada prioridad (alta, normal y baja), otro donde se ve lo mismo pero de las tareas terminadas junto a una tabla donde esta la opcion de volver a marcar una tarea como pendiente, y por ultimo un grafico de torta que indica el total de tareas pendientes y el total de tareas terminadas.
- Para aquellos usuarios con rol admin y creador, esta la seccion de listado de usuarios, donde pueden ver la totalidad de usuarios creados con la opcion de modificar el estado (dar de baja y dar de alta) y de modificar el rol a admin o usuario (esto ultimo solo lo puede hacer el creador)
- Opcion de modificar la contraseña
- Opcion de activar o desactivar el modo oscuro
