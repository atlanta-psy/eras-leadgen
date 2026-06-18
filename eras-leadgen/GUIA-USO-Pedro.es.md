# Guía de uso del agente de leads (Pedro)

El agente busca contactos de negocios de un nicho, los limpia, escribe ofertas personalizadas (en ruso, para clientes rusos) y te ayuda a enviarlas de forma segura: el correo se envía solo; Telegram y VK los envías tú a mano. El agente **no entra en tus cuentas** salvo el correo SMTP que tú configuras.

Todas las órdenes se ejecutan desde la carpeta del agente (`cd C:\leadgen`). El nicho de ejemplo es `guest_house` (casas de huéspedes).

---

## El proceso: 4 pasos para preparar la base

```
:: 1. Recoger leads desde OpenStreetMap por nicho
py leadgen.py collect --niche guest_house

:: 2. Enriquecer: entrar en las webs, encontrar email/Telegram/VK, detectar si ya tienen reservas, quitar duplicados
py enrich.py --niche guest_house

:: 3. Generar las ofertas personalizadas (asunto + mensaje + 2 seguimientos + propuesta corta)
py offer.py --niche guest_house
```

Resultado: el archivo `data\outreach_guest_house.csv` con una oferta lista por cada lead.

---

## El día a día

### Correo (automático)
```
py send_manager.py send-email --niche guest_house --dry-run   :: ver a quién se enviaría, SIN enviar
py send_manager.py send-email --niche guest_house             :: enviar de verdad
```
Envía los correos del día respetando el límite y el calentamiento (los primeros días pocos, va subiendo). Los seguimientos a quien no responde salen solos los días siguientes.

### Telegram / VK (a mano, mensaje personal)
```
py send_manager.py today --niche guest_house
```
Crea `data\today_guest_house_FECHA.csv` con la tanda del día para Telegram y VK. Abre el archivo, copia cada mensaje y envíalo tú desde una cuenta **aparte** (no la principal). Esto protege tus cuentas del bloqueo.

### Marcar quién responde
```
py send_manager.py replied --niche guest_house --name "Оливия"
```
El lead sale de la lista y no recibe más mensajes. Para descartar uno:
```
py send_manager.py skip --niche guest_house --name "Горки"
```

### Ver resultados
```
py send_manager.py stats --niche guest_house          :: embudo en consola
py send_manager.py dashboard --niche guest_house       :: tabla Excel: data\dashboard_guest_house.xlsx
```
El Excel tiene dos hojas: «Лиды» (cada lead con su estado, en colores) y «Воронка» (totales y % de respuesta). Ábrelo cuando quieras tras correr el comando.

---

## Rutina recomendada (cada mañana)
1. `send-email` (correo automático)
2. `today` → enviar la tanda de Telegram/VK a mano
3. marcar `replied` a quien contestó
4. `dashboard` para mirar la foto del día

---

## Qué puedes editar (es texto, no código)
- `configs\guest_house.yaml` — zonas geográficas y tipo de negocio a buscar.
- `configs\guest_house_offer.yaml` — todo el texto de la oferta: dolores, servicios, caso «Высокий Берег», promo, contactos, asunto, seguimientos.
- `configs\send_config.yaml` — límites diarios y calentamiento de cuentas.
- `configs\email_config.yaml` — tus datos de correo.

## Nuevo nicho
Copia los dos archivos `guest_house*.yaml`, renómbralos (ej. `restaurant.yaml` y `restaurant_offer.yaml`), cambia las zonas/etiquetas y el texto de la oferta, y usa `--niche restaurant`. El motor es el mismo.

---

## Seguridad (importante)
- El correo es el canal de volumen; usa un dominio aparte con SPF/DKIM y deja la línea de baja («отписаться»), ya incluida.
- Telegram/VK: cuentas **aparte**, nunca las principales; respeta los límites de `send_config.yaml`.
- El teléfono no se usa para envío masivo, solo para llamar si quieres.
- Empieza poco a poco (el calentamiento ya lo hace el agente) y sube el volumen con los días.
