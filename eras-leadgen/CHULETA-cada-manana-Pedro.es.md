# Chuleta: cada mañana (Pedro)

Memoria corta del día a día. Ejecuta las órdenes desde la carpeta del agente (`cd C:\leadgen`).

## Una vez — preparar la base (no cada día)
- `py leadgen.py collect --niche guest_house` — recoge casas y contactos
- `py enrich.py --niche guest_house` — añade email/Telegram/VK de las webs y quita duplicados
- `py offer.py --niche guest_house` — escribe las ofertas personalizadas
Con esto la base queda lista para enviar durante días/semanas.

## Cada mañana — 4 pasos (10 minutos)
1. **Correo** — `py send_manager.py send-email --niche guest_house` (el ordenador envía solo los correos del día). La primera vez puedes usar `--dry-run`: muestra a quién iría, sin enviar.
2. **Telegram/VK a mano** — `py send_manager.py today --niche guest_house` → se crea el archivo `today_...csv` con la tanda → copia el texto y envíalo desde una cuenta **aparte** (no la principal).
3. **Marcar quién responde** — `py send_manager.py replied --niche guest_house --name "Nombre"`.
4. **Ver la foto** — `py send_manager.py dashboard --niche guest_house` → abre el Excel `data\dashboard_guest_house.xlsx`.

Los seguimientos (2º y 3er toque) los añade el agente solo los días siguientes.

## Poner el correo en piloto automático (opcional)
Para que el correo se envíe solo cada mañana, usa el **Programador de tareas** de Windows:
1. Menú Inicio → escribe «Programador de tareas» → ábrelo.
2. «Crear tarea básica…» → nombre: `Correo leads`.
3. Desencadenador: **Diariamente** → elige la hora (ej. 09:00).
4. Acción: **Iniciar un programa** → «Examinar» → selecciona el archivo `enviar-correo-diario.bat` de la carpeta del agente.
5. Finalizar.
Requisitos: el ordenador debe estar encendido a esa hora y `email_config.yaml` bien rellenado. El calentamiento (pocos correos al principio) se mantiene solo.
Telegram y VK siguen siendo a mano.

## Si algo no va
- **No se envió el correo** → revisa `configs/email_config.yaml` (contraseña/servidor), o hoy el límite de calentamiento es bajo, o la base de hoy ya está procesada. Mira el archivo `data\email_log.txt`.
- **`today` sale vacío** → no quedan leads de Telegram/VK para hoy o se agotó el límite — es normal.
- **Quiero más correos al día** → sube los números en `configs/send_config.yaml`, pero solo después de la primera semana.
- **¿Quién respondió?** → las respuestas llegan a tu correo/Telegram normal; el agente no las ve. Míralas tú y marca `replied`.

## Regla de oro
Nunca uses tus cuentas principales para el envío en frío. Sube el volumen poco a poco. Así no te bloquean.
