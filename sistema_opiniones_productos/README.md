# Opiniones Inteligentes

Aplicación local para administrar productos y clientes, registrar opiniones y clasificarlas en español con PySentimiento. Flask sirve la interfaz en el puerto 5000; MySQL de XAMPP almacena los datos y Apache permite acceder a phpMyAdmin.

## Entorno verificado

En esta computadora se detectaron Python 3.13.14, Visual Studio Code, XAMPP en `C:\xampp`, Apache y MySQL activos. phpMyAdmin responde en `http://127.0.0.1/phpmyadmin/` y MySQL escucha en el puerto 3306. Se verificó la conexión de Python con el usuario `root` sin contraseña en `opiniones_productos` y se confirmó MariaDB 10.4.32.

PySentimiento 0.7.3 publica clasificadores de Python hasta 3.11. Aunque su metadato `Requires-Python` permite versiones anteriores a 4, Python 3.13 no figura entre sus clasificadores. Para una combinación conservadora, instala Python 3.11 de 64 bits antes de instalar las dependencias de este proyecto. PyTorch ofrece paquetes para Windows, pero la compatibilidad del conjunto debe mantenerse en el entorno certificado por PySentimiento.

## Tecnologías

- Python 3.11, Flask y Flask-WTF (CSRF).
- MySQL de XAMPP y `mysql-connector-python`.
- HTML5, CSS3 y JavaScript sin frameworks de frontend.
- PySentimiento 0.7.3 y PyTorch para sentimientos en español.
- Variables locales desde `.env`.

## Estructura

```text
sistema_opiniones_productos/
├── app.py
├── config.py
├── database.py
├── sentiment_analysis.py
├── requirements.txt
├── .env
├── .gitignore
├── database/
│   └── crear_base_datos.sql
├── templates/
├── static/
│   ├── css/styles.css
│   └── js/main.js
└── README.md
```

## Modelo de datos

- `productos`: catálogo editable.
- `clientes`: correo único; se crea automáticamente al registrar la primera opinión.
- `comentarios_productos`: relación de producto y cliente, texto y voto Like/Dislike.
- `analisis_comentarios`: resultado único por comentario, clase, probabilidad del modelo, palabras relevantes y fecha.

Las relaciones usan InnoDB y claves foráneas restrictivas: no se elimina un producto que tenga comentarios. El SQL emplea `CREATE ... IF NOT EXISTS` y datos de ejemplo idempotentes; no elimina ni reemplaza bases o tablas existentes. Si ya hay tablas homónimas con otra estructura, inspecciónalas antes de importar.

## Instalación en Windows

1. Instala Python 3.11 de 64 bits y la extensión Python de VS Code. En VS Code, abre esta carpeta (`sistema_opiniones_productos`) y selecciona el intérprete Python 3.11.
2. En la terminal PowerShell de VS Code confirma que `python --version` muestre `Python 3.11.x`. Si tu instalación tiene `py`, también puedes usar `py -3.11`.
3. Crea y activa el entorno virtual:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   Si PowerShell bloquea la activación, puedes ejecutar los comandos con el intérprete directamente:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Instala las dependencias:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   PyTorch puede ocupar bastante espacio. Para una instalación solo CPU, sigue el selector oficial de instalación de PyTorch para Windows y Python, luego instala el resto de `requirements.txt`.

5. Inicia Apache y MySQL desde el panel de XAMPP. Comprueba `http://127.0.0.1/phpmyadmin/`.
6. En phpMyAdmin selecciona **Importar**, elige `database/crear_base_datos.sql` y ejecuta la importación. El script no contiene `DROP` y no borra bases existentes.
7. Abre `.env` y sustituye `CHANGE_ME` por la contraseña real configurada para el usuario MySQL indicado. Si ese usuario está configurado deliberadamente sin contraseña, deja `DB_PASSWORD=` vacío. No cambies una contraseña de XAMPP desde este proyecto.
8. Comprueba la conexión:

   ```powershell
   python -m flask --app app check-db
   ```

9. Inicia Flask:

   ```powershell
   python app.py
   ```

10. Abre <http://127.0.0.1:5000>.

Los comandos de Python y Flask deben ejecutarse desde la carpeta de este proyecto con `.venv` activo. Flask escucha solo en `127.0.0.1`; Apache (puerto 80), MySQL (3306) y Flask (5000) son servicios distintos.

## Configuración

`.env` contiene:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=CHANGE_ME
DB_NAME=opiniones_productos
SECRET_KEY=<clave aleatoria local>
FLASK_DEBUG=0
```

`.env` está excluido de Git. Usa la cuenta y contraseña reales configuradas en MySQL; el proyecto no presupone que `root` esté sin contraseña. La clave secreta que acompaña el archivo local debe cambiarse por una clave aleatoria propia antes de publicar o exponer el servicio.

## Uso y análisis

1. Crea o edita productos en **Productos**.
2. Registra una opinión en **Nuevo comentario**. La aplicación valida los campos, normaliza el correo y reutiliza al cliente existente por correo. El voto es independiente del sentimiento detectado.
3. Consulta comentarios y clientes en sus páginas respectivas.
4. En **Análisis IA**, analiza comentarios individuales o los pendientes. Un resultado existente no se sobrescribe.
5. Revisa la clase POSITIVO, NEGATIVO o NEUTRAL, la probabilidad asignada por el modelo y las palabras más frecuentes no funcionales del texto.
6. Consulta los indicadores agregados desde **Panel**.

La primera inicialización del analizador descarga los pesos del modelo y necesita conexión a Internet. Luego Transformers/PySentimiento los conserva en su caché local. La confianza es la probabilidad de clase que proporciona el modelo, no una medición de precisión. Sarcasmo, contexto, negaciones y ambigüedad pueden afectar la clasificación.

Si PySentimiento o el modelo no se carga, la interfaz muestra un error controlado y no registra una clasificación inventada. No se incluye una alternativa basada en palabras positivas/negativas.

## Seguridad y validaciones

- Consultas SQL parametrizadas y transacciones con rollback ante errores.
- Escape HTML automático de Jinja y formularios protegidos por CSRF.
- Validación de nombre, correo, producto, comentario y voto del lado del servidor.
- Credenciales fuera del código y errores internos registrados en el servidor.
- Las eliminaciones respetan dependencias entre productos y comentarios.

Esta aplicación es para uso local de desarrollo; antes de publicarla se debe configurar HTTPS, una cuenta MySQL con privilegios mínimos, una clave secreta propia y un servidor WSGI de producción.

## Pruebas y estado

Se verificaron: existencia de Python, VS Code y XAMPP; Apache, MySQL y phpMyAdmin activos; importación no destructiva del SQL cuando la base aún no existía; conexión de Python mediante `check-db`; y respuesta HTTP 200 en Inicio, Panel, Productos, Clientes, Comentarios, Nuevo comentario y Análisis usando la base local. También se probaron por separado la validación de formularios, CSRF, escape HTML, y el guardado simulado del resultado del modelo. La instalación/inferencia real de PySentimiento y las operaciones CRUD que escriben registros quedan pendientes.

Después de configurar la base, comprueba: alta de producto, alta/reutilización de cliente, comentarios positivo/negativo/neutral, persistencia de votos, análisis individual y masivo, unicidad de resultados, cifras del panel y manejo de credenciales erróneas. El comando `check-db` valida conectividad y credenciales sin modificar datos.

## Limitaciones conocidas

- La confianza del modelo no garantiza exactitud ni sustituye una revisión humana.
- El análisis inicial puede tardar y requiere Internet para descargar el modelo.
- La cuenta de acceso es de administración local; no hay autenticación de usuarios.
- No existe eliminación de clientes desde la interfaz, para evitar romper relaciones.
