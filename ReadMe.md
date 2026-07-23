# Guía de ejecución del proyecto

Este documento describe los pasos necesarios para configurar y ejecutar el proyecto correctamente.

---

## Requisitos previos

Antes de iniciar, es necesario tener instalado:

- Python 3.x
- Docker Desktop

---

# Paso 1 - Levantar la base de datos con Docker

Primero se debe iniciar **Docker Desktop**.

Luego, abrir una terminal ubicada en el **directorio raíz del proyecto**, es decir, la carpeta donde se encuentra el archivo:

```text
docker-compose.yml
```

Ejecutar el siguiente comando:

```bash
docker compose up -d --build
```

Este comando realizará las siguientes acciones:

- Construirá las imágenes necesarias para el proyecto.
- Creará e iniciará el contenedor de la base de datos.
- Ejecutará el archivo `schema.sql`.
- Creará las tablas necesarias.
- Insertará los registros iniciales definidos en `schema.sql`.

---

# Paso 2 - Crear el entorno virtual de Python

Desde la terminal, ubicarse en el directorio raíz del proyecto.

Ejecutar:

```bash
python -m venv venv
```

Este comando creará un entorno virtual llamado `venv`, donde se instalarán las dependencias del proyecto.

---

# Paso 3 - Activar el entorno virtual

Ejecutar el siguiente comando:

```powershell
.\venv\Scripts\Activate.ps1
```

Si el entorno se activó correctamente, la terminal mostrará un prefijo indicando que el entorno virtual está activo.

Ejemplo:

```powershell
(venv) PS C:\ruta_del_proyecto\agente>
```

---

# Paso 4 - Instalar las dependencias del proyecto

Con el entorno virtual activo, ejecutar:

```bash
pip install -r requirements.txt
```

Este comando instalará todas las librerías necesarias para ejecutar el proyecto.

---

# Paso 5 - Probar procesamiento del JSON generado por agente de voz

Este proceso realiza las siguientes acciones:
- Lee el archivo `resultado_llamada.json`
- Valida la estructura del JSON.
- Inserta la información validada en la base de datos en la tabla agent_predictions .

Para ejecutarlo, desde la raíz del proyecto ejecutar:

```bash
python app/postllamada.py
```

---

# Paso opcional - Probar el agente de voz

Si se desea probar el agente de voz y verificar cómo genera el JSON, primero es necesario configurar la API KEY.

## Configuración de la API KEY

En el directorio raíz del proyecto crear un archivo llamado:

```text
.env
```

Dentro del archivo agregar:

```env
API_KEY=TU_API_KEY
```

Reemplazar:

```text
TU_API_KEY
```

por la API KEY correspondiente.

Una vez configurada la variable de entorno, ejecutar:

```bash
python app/agente.py
```

Si la API KEY es válida, el agente se ejecutará correctamente.

---

Una vez que termine la ejecución del agente, este generará un archivo JSON que tiene la siguiente estructura:
```text
call_result_{LEAD_ID}_{CALL_ID}.json
```

---

# Comandos adicionales de Docker

## Detener el contenedor sin eliminarlo

Si se desea detener temporalmente el contenedor y conservarlo:

```bash
docker compose stop
```

---

## Detener y eliminar los contenedores

Si se desea detener y eliminar los contenedores creados por Docker Compose:

```bash
docker compose down
```

---

# Solución de problemas - Imagen de Docker en caché

En algunos casos, Docker puede utilizar una imagen almacenada en caché y no reflejar los últimos cambios realizados en el archivo `schema.sql`.

Esto puede ocurrir cuando se modifica la estructura de la base de datos y Docker reutiliza una imagen creada anteriormente.

Si esto sucede, se recomienda eliminar el contenedor y la imagen actual para reconstruir la imagen y el contenedor de la base de datos desde cero.

---

## Opción 1 - Eliminar manualmente la imagen Docker

Primero listar las imágenes disponibles:

```bash
docker images
```

La imagen generada por Docker Compose tendrá normalmente el siguiente nombre:

```text
agente-postgres_db
```

Esto ocurre porque Docker Compose al generar el nombre de la imagen docker lo estructura asi:

```text
<nombre_del_proyecto>-<nombre_del_servicio>
```



Comando para eliminar la imagen:

```bash
docker rmi agente-postgres_db
```

Si Docker indica que la imagen está siendo utilizada por un contenedor, primero se debe de detener y eliminar los contenedores:

```bash
docker compose down
```

Luego se ejecuta nuevamente:

```bash
docker rmi agente-postgres_db
```

Finalmente reconstruir la imagen y crear nuevamente el contenedor:

```bash
docker compose up -d --build
```

---

# Información del contenedor de base de datos

Según la configuración del archivo `docker-compose.yml`:

```yaml
container_name: postgres_sistema_empresa
```

El contenedor creado tendrá el nombre:

```text
postgres_sistema_empresa
```

La imagen generada tendrá el nombre:

```text
agente-postgres_db
```

# Estructura del proyecto

```text
agente/
│
├── .ipynb_checkpoints/
├── app/
│   ├── jsons/
│   │   ├── call_result_13_3.json
│   │   └── resultado_llamada.json
│   ├── agente.py
│   ├── postllamada.py
│   └── pruebas.py
├── venv/
├── .env
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── ReadMe.md
├── requirements.txt
└── schema.sql