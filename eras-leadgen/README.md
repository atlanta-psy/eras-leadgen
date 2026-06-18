# Eras Leadgen — агент лидогенерации

Локальная программа: собирает контакты бизнесов в нише (из OpenStreetMap), обогащает с сайтов (email/Telegram/VK, наличие брони), пишет персональные офферы и помогает безопасно рассылать с прогревом, фоллоу-апами и трекером. Отправку запускаете вы; почта может слаться автоматически через ваш SMTP.

## Документация
- Русский: `КАК-РАБОТАЕТ.md`
- Español (instalación): `INSTALACION-Pedro.es.md`
- Español (uso): `GUIA-USO-Pedro.es.md`

## Установка
```
pip install -r requirements.txt
```

## Конвейер
```
python leadgen.py collect --niche guest_house
python vk_collect.py --niche guest_house     # по желанию: ВК-сообщества (нужен токен ВК)
python enrich.py  --niche guest_house
python offer.py   --niche guest_house
python send_manager.py send-email --niche guest_house --dry-run
python send_manager.py today      --niche guest_house
python send_manager.py dashboard  --niche guest_house
```

## Конфиги (правятся без кода)
- `configs/guest_house.yaml` — районы и теги ниши
- `configs/guest_house_offer.yaml` — весь текст оффера
- `configs/send_config.yaml` — лимиты и прогрев
- `configs/email_config.yaml` — SMTP (НЕ коммитить с реальным паролем)

Офферы генерируются на русском (для клиентов в РФ). Инструкции для Педро — на испанском.
