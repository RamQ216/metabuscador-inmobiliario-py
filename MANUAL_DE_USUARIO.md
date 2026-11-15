# MANUAL DE USUARIO DEL SISTEMA
**Proyecto:** Metabuscador y Comparador Cruzado Inmobiliario de Paraguay  
**Normalización de Datos:** 10 Tablas en 3ra Forma Normal (3FN)  
**Moneda Unificada:** Guaraníes (`PYG / Gs.`)

---

## 1. Introducción
El presente sistema permite buscar casas, departamentos y dúplex en **Asunción y Gran Asunción** agrupando automáticamente las publicaciones que corresponden al mismo inmueble físico pero son comercializadas simultáneamente por distintas inmobiliarias (**RE/MAX Paraguay** e **InfoCasas Paraguay**). De esta forma, el usuario puede identificar diferencias de precio, expensas y metros cuadrados reportados antes de agendar una visita.

---

## 2. Procedimiento de Ingreso al Sistema (Login — Requisito 8.2)
1. En la barra superior derecha del sistema, haga clic en el botón **`Ingresar al Sistema`**.
2. Se abrirá la ventana de Control de Acceso.
3. Para pruebas y evaluación académica, puede utilizar los botones de **Acceso Rápido en 1 Clic** o ingresar manualmente:
   - **Perfil Administrador:**
     - **Correo:** `admin@inmueblespy.com`
     - **Contraseña:** `admin123`
   - **Perfil Cliente:**
     - **Correo:** `maria@gmail.com`
     - **Contraseña:** `cliente123`
4. Haga clic en **`Iniciar Sesión`**. En la barra superior aparecerá su nombre y rol activo. Para salir en cualquier momento, presione el botón **`Salir`**.

---

## 3. Navegación por el Menú Principal (Requisito 8.3)
El sistema cuenta con un menú principal numerado en la parte superior dividido en **4 módulos**:
- **`01 Explorador & Mapa`**: Buscador general, filtros por ciudad/barrio, tarjetas con alertas de ahorro y mapa interactivo agrupado por clusters.
- **`02 Comparador Cruzado`**: Tabla comparativa lado a lado entre inmobiliarias (Precio en PYG, Expensas y Superficie) y formulario de solicitud de visita.
- **`03 Movimientos (Visitas)`**: Historial y gestión de estados de las Solicitudes de Visita Comparada (Cabecera y Detalle).
- **`04 Mantenimientos (ABM)`**: Administración de las tablas maestras del sistema y ejecución del motor de scraping/deduplicación.

---

## 4. Uso del Explorador y Mapa Georreferenciado (Módulo 01)
1. Seleccione los criterios deseados en la barra de filtros:
   - **Operación:** Alquiler mensual o Venta definitiva.
   - **Ciudad y Barrio:** Seleccione entre Asunción, Luque, San Lorenzo, Fernando de la Mora, Lambaré o Mariano Roque Alonso.
   - **Tipo de Unidad:** Departamento, Casa o Dúplex.
   - **Dormitorios y Precio Máximo en Guaraníes (`Gs.`).**
   - **Casilla `Solo multi-agencia`:** Márquela si desea ver únicamente los inmuebles donde se detectaron dos o más inmobiliarias compitiendo por la misma propiedad.
2. Presione **`Filtrar`**.
3. En la columna izquierda verá las propiedades encontradas. Aquellas con múltiples ofertas mostrarán una etiqueta verde indicando cuántas agencias la publican y la **diferencia en Guaraníes detectada**.
4. En la columna derecha verá el **Mapa OpenStreetMap con Clusters** (círculos numerados que se abren al hacer clic o zoom) y el **Índice Referencial de Gs./m² por Barrio**.

---

## 5. Comparación Cruzada y Registro de Movimiento (Módulo 02 y Requisito 8.1)
1. En cualquier propiedad del listado o del mapa, haga clic en **`Comparar ofertas →`**.
2. El sistema abrirá la vista comparativa mostrando lado a lado cada agencia inmobiliaria con los 3 indicadores clave:
   - **1. Precio Normalizado en Guaraníes (`PYG`).**
   - **2. Expensas Mensuales Reportadas (`PYG`).**
   - **3. Superficie Reportada (`m²`) y Costo Mensual Real (Precio + Expensas).**
3. **Procedimiento para registrar el Movimiento (`Solicitud de Visita Comparada`):**
   - En el bloque inferior **"Generar Solicitud de Visita Comparada"**, marque las casillas de las agencias que desea incluir en el detalle de su solicitud.
   - Elija la **Fecha de Visita Propuesta** y la **Franja Horaria** (*Mañana, Siesta o Tarde*).
   - Escriba cualquier consulta en **Observaciones** y presione **`Registrar Movimiento de Visita`**.
   - El sistema guardará la cabecera en la tabla `solicitudes_visita` y congelará los precios vigentes de cada agencia en la tabla `solicitud_detalles`.

---

## 6. Gestión de Movimientos Registrados (Módulo 03 — Requisito 8.1)
1. Ingrese al menú **`03 Movimientos (Visitas)`**.
2. Verá cada solicitud registrada con su número de operación, fecha, solicitante, propiedad y la tabla de **Detalle** con los precios congelados por agencia.
3. Para cambiar el estado de una solicitud, utilice el selector desplegable de la derecha (`PENDIENTE`, `CONFIRMADA`, `REALIZADA`, `CANCELADA`). El cambio se guarda automáticamente en la base de datos.
4. Para anular y borrar un registro, haga clic en **`Eliminar`**.

---

## 7. Mantenimientos del Sistema / ABMs (Módulo 04 — Requisito 8.4)
1. Ingrese al menú **`04 Mantenimientos (ABM)`**.
2. Seleccione cualquiera de las pestañas para realizar Altas, Bajas y Consultas sobre las tablas normalizadas en 3FN:
   - **`1. Agencias Inmobiliarias`**: Registrar nuevas inmobiliarias o eliminar existentes sin publicaciones.
   - **`2. Barrios y Coordenadas`**: Agregar barrios con su latitud y longitud centroide asociada a una ciudad.
   - **`3. Ciudades`**: Dar de alta nuevos municipios.
   - **`4. Tipos de Inmueble`**: Agregar categorías de propiedades.
   - **`5. Usuarios y Roles`**: Crear cuentas de usuario asignando rol *Administrador* o *Cliente*.
   - **`6. Simulador Manual de Cruce (Scoring)`**: Permite ingresar un aviso de prueba o presionar el botón superior **`▶ Ejecutar Scraper & Deduplicación`** para comprobar en vivo cómo el algoritmo de puntaje agrupa propiedades idénticas.
