# Instalación del agente de generación de leads (Windows)

Guía para Pedro. El agente funciona en ruso (los mensajes a clientes se generan en ruso), pero esta guía está en español. Sigue los pasos en orden.

---

## 1. Instalar Python

1. Abre https://www.python.org/downloads/windows/
2. Descarga el instalador «Windows installer (64-bit)» de Python 3.12 o superior.
3. Ejecuta el instalador. **MUY IMPORTANTE:** marca la casilla **«Add python.exe to PATH»** abajo, antes de pulsar «Install Now».
4. Termina la instalación.

Comprueba (abre el menú Inicio → escribe «cmd» → Enter para abrir la consola, y escribe):
```
py --version
```
Debe mostrar `Python 3.12.x` o superior.

---

## 2. Copiar la carpeta del agente

Copia la carpeta `leadgen` a un sitio cómodo, por ejemplo `C:\leadgen`.
Todas las órdenes se ejecutan desde esa carpeta. En la consola entra en ella:
```
cd C:\leadgen
```

---

## 3. Instalar las librerías necesarias
```
py -m pip install pyyaml openpyxl
```
Espera a que termine («Successfully installed …»).

---

## 4. Configurar tu correo (para el envío automático)

Abre con el Bloc de notas el archivo `configs\email_config.yaml` y rellena tus datos:

- `smtp_host` — servidor de salida de tu dominio (lo da tu hosting; ej. `smtp.timeweb.ru`, `smtp.yandex.ru`).
- `smtp_port` y `use_ssl` — 465 con SSL (`use_ssl: true`), o 587 con TLS (`use_ssl: false`).
- `smtp_user` — normalmente tu propio email.
- `smtp_password` — la contraseña del correo o una **contraseña de aplicación** (recomendado).
- `from_email` y `from_name` — desde qué dirección y con qué nombre se envía.

Guarda el archivo.

> Consejo: usa un dominio/buzón **aparte** para el frío, no tu correo principal de trabajo. Y antes de enviar en volumen, conviene tener configurado SPF/DKIM en el dominio (lo hace el panel del hosting) para no caer en spam.

---

## 5. Comprobar que todo arranca
```
py leadgen.py
```
Debe mostrar la ayuda con los comandos. Si la ves, está listo.

Ahora pasa a la guía de uso: **GUIA-USO-Pedro.es.md**.

---

## Problemas frecuentes
- **`py` no se reconoce** → no marcaste «Add to PATH»; reinstala Python marcando esa casilla.
- **error al instalar librerías** → ejecuta la consola «como administrador» y repite el paso 3.
- **el correo da error de login** → usa una «contraseña de aplicación» en lugar de la normal, y revisa `smtp_host`/`smtp_port`.
